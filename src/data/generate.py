"""Generate a synthetic patient dataset from a YAML config.

    python -m src.data.generate --config configs/sim_v2.yaml

Writes to the config's `output_dir`:
- patients.csv  one row per patient (labels, context, observed onsets, split)
- events.csv    full symptom courses with `observed` and `onset_assumed` flags
- meta.json     config, git commit, knowledge-file hashes, verification status per table,
                experiment type, assumptions in force, SIMULATED flag
- report.md     sanity report and rule-based baseline (src/data/report.py)
- onset_diagnostics.md  copula / onset-order checks (src/data/diagnostics.py)

`experiment_type: primary` (the default) uses cited evidence only; assumption-based
settings such as `onset_fallback` are refused unless the config says
`experiment_type: sensitivity`.

`unknown_onset` says what happens to clinical rows with a cited frequency but no cited onset
window: `exclude` (default; drop the row), `label_only` (the symptom occurs and counts toward
the label, but has no onset time and is never observed by the model), or `fallback` (fill
the window from `onset_fallback`; the default when `onset_fallback` is set).

All outputs are SIMULATION data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import yaml

from src.data.diagnostics import onset_diagnostics
from src.data.diagnostics import render as render_diagnostics
from src.data.diagnostics import summarise as summarise_diagnostics
from src.data.knowledge import (
    apply_overrides,
    load_knowledge,
    read_bib_keys,
    split_keys,
    verification_summary,
)
from src.data.presentation import DelayDistribution, load_delay
from src.data.report import baseline_metrics, build_report, rule_predictions
from src.data.simulator import (
    DEFAULT_MAX_ORDER_TRIES,
    DEFAULT_PRECEDENCE,
    UNKNOWN_ONSET_MODES,
    SpeciesSpec,
    assign_splits,
    build_specs,
    check_count,
    count_fallback_rows,
    events_dataframe,
    simulate_patients,
    to_dataframe,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPLITS = {"train": 0.6, "calibration": 0.2, "test": 0.2}
PRIMARY, SENSITIVITY = "primary", "sensitivity"
FALLBACK = "fallback"


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
    if not (math.isfinite(lo) and math.isfinite(hi) and 0 <= lo <= hi):
        raise ValueError("onset_fallback hours must be finite with 0 <= lo <= hi")
    return lo, hi


def presentation_delay(config: dict[str, Any], knowledge_dir: Path) -> DelayDistribution | None:
    """The cited delay distribution from `config['presentation_delay']`, or None (uniform range)."""
    spec = config.get("presentation_delay")
    if not spec:
        return None
    return load_delay(
        knowledge_dir, spec["profile"], float(spec["open_bin_max_hours"]),
        require_verified=config.get("require_verified", False),
    )


def experiment_type(config: dict[str, Any], fallback: tuple[float, float] | None) -> str:
    """`primary` (evidence only) or `sensitivity`; assumption-based settings need the latter."""
    kind = config.get("experiment_type", PRIMARY)
    if kind not in {PRIMARY, SENSITIVITY}:
        raise ValueError(f"experiment_type must be {PRIMARY!r} or {SENSITIVITY!r}")
    if fallback is not None and kind != SENSITIVITY:
        raise ValueError(
            "onset_fallback fills unknown onsets with an assumed window; it is only allowed in "
            "configs labelled `experiment_type: sensitivity`"
        )
    return kind


def unknown_onset_mode(config: dict[str, Any], fallback: tuple[float, float] | None) -> str:
    """`exclude`, `label_only` or `fallback`, checked against `onset_fallback`."""
    mode = config.get("unknown_onset", FALLBACK if fallback is not None else "exclude")
    if mode not in UNKNOWN_ONSET_MODES | {FALLBACK}:
        raise ValueError(f"unknown_onset must be one of {sorted(UNKNOWN_ONSET_MODES | {FALLBACK})}")
    if (mode == FALLBACK) != (fallback is not None):
        raise ValueError("unknown_onset: fallback needs onset_fallback, and onset_fallback needs unknown_onset: fallback")
    return mode


def assumptions(
    config: dict[str, Any], fallback: tuple[float, float] | None, specs: dict[str, SpeciesSpec], mode: str,
) -> list[str]:
    """Simulation assumptions (not clinical evidence) in force for this dataset."""
    items = [
        f"severity_correlation {config.get('severity_correlation', 0.0)} (Gaussian copula; no cited value)",
        "onset uniform within each cited window before copula skew and ordering",
        "species mix " + ("from species_weights (config)" if config.get("species_weights") else "uniform"),
        "GPS and month uniform (placeholder until the Phase 3 geo prior)",
        "hour of day uniform within the cited day/night half",
    ]
    if mode == FALLBACK:
        items.append(f"ASSUMPTION: onset_fallback window {fallback} h for rows with unknown onset")
    elif mode == "label_only":
        items.append(
            "symptoms with unknown onset occur at their cited frequency and count toward the label, "
            "but have no onset time and are never part of the model input (treated as not yet "
            "recognised at presentation)"
        )
    else:
        items.append("rows with unknown onset are excluded, so those symptoms never occur")
    delay = config.get("presentation_delay")
    if delay:
        items.append(
            f"open presentation-delay bin capped at {delay['open_bin_max_hours']} h; uniform within bins; "
            "unreported share of the source assumed to follow the reported bins"
        )
    else:
        items.append(f"presentation delay uniform {config.get('presentation_hours', (0.5, 24.0))} h (uncited)")
    marginal_only = sorted(s for s, spec in specs.items() if spec.joint_context is None and spec.context)
    if marginal_only:
        items.append(f"context flags drawn independently (no cited joint counts) for {marginal_only}")
    return items


def generate(config: dict[str, Any]) -> Path:
    """Simulate patients per `config` and write the dataset; returns the output dir."""
    knowledge_dir = resolve(config.get("knowledge_dir", "knowledge"))
    fallback = onset_fallback(config, knowledge_dir)
    kind = experiment_type(config, fallback)
    mode = unknown_onset_mode(config, fallback)
    sim_mode = "exclude" if mode == FALLBACK else mode
    kb = load_knowledge(
        knowledge_dir,
        require_citations=config.get("require_citations", False),
        require_verified=config.get("require_verified", False),
        allow_missing_onset=True,  # unknown-onset rows are counted here and excluded or filled in build_specs
    )
    kb = apply_overrides(kb, config.get("knowledge_overrides"))
    precedence = tuple(config.get("syndrome_precedence", DEFAULT_PRECEDENCE))
    delay = presentation_delay(config, knowledge_dir)
    rho = float(config.get("severity_correlation", 0.0))
    max_tries = int(config.get("max_order_tries", DEFAULT_MAX_ORDER_TRIES))
    patients = simulate_patients(
        kb,
        n=check_count(config["n_patients"], "n_patients"),
        seed=int(config["seed"]),
        species_weights=config.get("species_weights"),
        presentation_hours_range=tuple(config.get("presentation_hours", (0.5, 24.0))),
        precedence=precedence,
        onset_fallback=fallback,
        severity_correlation=rho,
        presentation_delay=delay,
        max_order_tries=max_tries,
        unknown_onset=sim_mode,
    )
    table = to_dataframe(patients)
    table["split"] = assign_splits(len(patients), config.get("splits", DEFAULT_SPLITS), int(config["seed"]))

    out = resolve(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "patients.csv", index=False)
    events = events_dataframe(patients)
    events.to_csv(out / "events.csv", index=False)

    specs = build_specs(kb, fallback, sim_mode)
    n_diag = check_count(config.get("diagnostics_n_per_species", 2000), "diagnostics_n_per_species")
    marginals, pairs = onset_diagnostics(specs, n_diag, int(config["seed"]), rho, max_tries)
    (out / "onset_diagnostics.md").write_text(render_diagnostics(marginals, pairs, n_diag), encoding="utf-8")

    n_unknown = count_fallback_rows(kb)
    test = [p for p, s in zip(patients, table["split"]) if s == "test"] if patients else []
    baseline = (
        baseline_metrics([p.venom_syndrome for p in test], rule_predictions(test, kb.marker_of(), precedence))
        if test else {}
    )
    verification = verification_summary(knowledge_dir)
    meta = {
        "SIMULATED": True,
        "note": "Synthetic patients from a literature-derived table. Results are simulation results.",
        "experiment_type": kind,
        "config": config,
        "git_commit": git_commit(),
        "knowledge_hashes": file_hashes(knowledge_dir),
        "verification": verification,
        "n_rows_unverified": sum(t["unverified"] for t in verification.values()),
        "require_verified": bool(config.get("require_verified", False)),
        "unknown_onset": mode,
        "assumptions": assumptions(config, fallback, specs, mode),
        "n_patients": len(patients),
        "n_clinical_rows_using_onset_fallback": n_unknown if mode == FALLBACK else 0,
        "n_clinical_rows_excluded_unknown_onset": n_unknown if mode == "exclude" else 0,
        "n_clinical_rows_label_only": n_unknown if mode == "label_only" else 0,
        "n_events_with_assumed_onset": int(events["onset_assumed"].sum()) if len(events) else 0,
        "n_events_with_unknown_onset": int(events["onset_unknown"].sum()) if len(events) else 0,
        # Envenomed (not dry-bite) patients whose sampled course is empty: they get the dry label
        # although the bite was not dry (a label artefact, large when unknown onsets are excluded).
        "n_envenomed_without_any_symptom": sum(
            1 for p in patients if specs[p.species].venomous and not p.dry_bite and not p.course
        ),
        "n_patients_with_order_violations": int((table["order_violations"] > 0).sum()) if len(table) else 0,
        "onset_diagnostics": summarise_diagnostics(marginals, pairs),
        "joint_context_species": sorted(s for s, spec in specs.items() if spec.joint_context is not None),
        "presentation_delay": delay.summary() if delay else None,
        "presentation_hours_summary": (
            table["presentation_hours"].describe(percentiles=[0.25, 0.5, 0.75]).round(2).to_dict()
            if len(table) else {}
        ),
        "syndrome_counts": table["venom_syndrome"].value_counts().to_dict() if len(table) else {},
        "rule_baseline_test": baseline,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    if patients:
        notes = report_notes(meta, config, fallback, delay)
        report = build_report(patients, table["split"].tolist(), kb, precedence, notes)
        (out / "report.md").write_text(report, encoding="utf-8")
    return out


def report_notes(
    meta: dict[str, Any], config: dict[str, Any], fallback: tuple[float, float] | None,
    delay: DelayDistribution | None,
) -> list[str]:
    verification = ", ".join(f"{k} {v['unverified']}/{v['rows']}" for k, v in meta["verification"].items())
    return [
        f"config `{config['name']}` ({meta['experiment_type']} experiment), seed {config['seed']}, "
        f"commit `{meta['git_commit']}`",
        {
            FALLBACK: f"ASSUMPTION: {meta['n_clinical_rows_using_onset_fallback']} clinical row(s) use the "
                      f"fallback onset window {fallback}",
            "label_only": f"{meta['n_clinical_rows_label_only']} clinical row(s) with unknown onset are label-only "
                          f"({meta['n_events_with_unknown_onset']} events count toward labels, never observed)",
            "exclude": f"{meta['n_clinical_rows_excluded_unknown_onset']} clinical row(s) with unknown onset excluded",
        }[meta["unknown_onset"]],
        f"{meta['n_rows_unverified']} knowledge row(s) not yet human-verified ({verification})",
        f"{meta['n_envenomed_without_any_symptom']} envenomed (non-dry-bite) patient(s) have no symptom in "
        "their course and are labelled non-venomous/dry (label artefact)",
        f"{meta['n_patients_with_order_violations']} patient(s) still violate an onset order "
        "(see onset_diagnostics.md)",
        (f"presentation delay: cited profile `{config['presentation_delay']['profile']}` "
         f"(unreported share of source {delay.unreported:.0%})" if delay
         else f"presentation delay: uniform {config.get('presentation_hours', (0.5, 24.0))} h (uncited)"),
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    out = generate(load_config(args.config))
    print(f"wrote simulated dataset to {out}")


if __name__ == "__main__":
    main()
