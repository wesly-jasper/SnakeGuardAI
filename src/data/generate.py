"""Generate a synthetic patient dataset from a YAML config.

    python -m src.data.generate --config configs/sim_v1.yaml

Writes to the config's `output_dir`:
- patients.csv  one row per patient (labels, context, observed onsets, split)
- events.csv    full symptom courses with an `observed` flag
- meta.json     config, git commit, knowledge-file hashes, SIMULATED flag
- report.md     sanity report and rule-based baseline (src/data/report.py)

All outputs are SIMULATION data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from src.data.knowledge import load_knowledge, read_bib_keys, split_keys
from src.data.report import build_report
from src.data.simulator import (
    DEFAULT_PRECEDENCE,
    assign_splits,
    count_fallback_rows,
    events_dataframe,
    simulate_patients,
    to_dataframe,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPLITS = {"train": 0.6, "calibration": 0.2, "test": 0.2}


def load_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key in ("name", "seed", "n_patients", "output_dir"):
        if key not in config:
            raise ValueError(f"config missing required key: {key}")
    return config


def git_commit(repo: Path = REPO_ROOT) -> str:
    """Current commit hash, suffixed with `-dirty` if the tree has changes."""
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

    try:
        return run("rev-parse", "HEAD") + ("-dirty" if run("status", "--porcelain") else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def file_hashes(directory: Path) -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.iterdir())
        if p.suffix in {".csv", ".bib"}
    }


def resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def onset_fallback(config: dict[str, Any], knowledge_dir: Path) -> tuple[float, float] | None:
    """The cited fallback onset window from `config`, or None if not configured."""
    spec = config.get("onset_fallback")
    if not spec:
        return None
    keys = split_keys(spec.get("source_key", ""))
    if not keys or not set(keys) <= read_bib_keys(knowledge_dir / "sources.bib"):
        raise ValueError("onset_fallback needs a source_key present in sources.bib")
    lo, hi = (float(h) for h in spec["hours"])
    if not 0 <= lo <= hi:
        raise ValueError("onset_fallback hours must satisfy 0 <= lo <= hi")
    return lo, hi


def generate(config: dict[str, Any]) -> Path:
    """Simulate patients per `config` and write the dataset; returns the output dir."""
    knowledge_dir = resolve(config.get("knowledge_dir", "knowledge"))
    fallback = onset_fallback(config, knowledge_dir)
    kb = load_knowledge(
        knowledge_dir,
        require_citations=config.get("require_citations", False),
        require_verified=config.get("require_verified", False),
        allow_missing_onset=fallback is not None,
    )
    precedence = tuple(config.get("syndrome_precedence", DEFAULT_PRECEDENCE))
    patients = simulate_patients(
        kb,
        n=int(config["n_patients"]),
        seed=int(config["seed"]),
        species_weights=config.get("species_weights"),
        presentation_hours_range=tuple(config.get("presentation_hours", (0.5, 24.0))),
        precedence=precedence,
        onset_fallback=fallback,
    )
    table = to_dataframe(patients)
    table["split"] = assign_splits(len(patients), config.get("splits", DEFAULT_SPLITS), int(config["seed"]))

    out = resolve(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "patients.csv", index=False)
    events_dataframe(patients).to_csv(out / "events.csv", index=False)
    n_fallback = count_fallback_rows(kb) if fallback else 0
    meta = {
        "SIMULATED": True,
        "note": "Synthetic patients from a literature-derived table. Results are simulation results.",
        "config": config,
        "git_commit": git_commit(),
        "knowledge_hashes": file_hashes(knowledge_dir),
        "n_patients": len(patients),
        "n_clinical_rows_using_onset_fallback": n_fallback,
        "n_rows_unverified": int((~kb.clinical["verified"]).sum() + (~kb.context["verified"]).sum()),
        "syndrome_counts": table["venom_syndrome"].value_counts().to_dict() if len(table) else {},
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    if patients:
        notes = [
            f"config `{config['name']}`, seed {config['seed']}, commit `{meta['git_commit']}`",
            f"{n_fallback} clinical row(s) use the fallback onset window {fallback}" if fallback else "no onset fallback",
            f"{meta['n_rows_unverified']} knowledge row(s) not yet human-verified",
        ]
        report = build_report(patients, table["split"].tolist(), kb, precedence, notes)
        (out / "report.md").write_text(report, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    out = generate(load_config(args.config))
    print(f"wrote simulated dataset to {out}")


if __name__ == "__main__":
    main()
