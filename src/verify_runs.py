"""Verify Phase 2 training runs against their dataset and saved predictions.

    python -m src.verify_runs outputs/phase2/sim_v2 [more run dirs]

Checks per run directory (written by src.train):
1. run.json status is `complete` and its commit equals the current `git rev-parse HEAD`
   (reported, with the dirty flag, not silently accepted).
2. Saved predictions contain only calibration and test patients, each in the split the
   dataset assigns, with the dataset's labels.
3. For every model seed, the fit and validation patients come from the train split only
   and are disjoint from calibration and test (recomputed with the same seeded split).
4. Calibrators were fitted on exactly the calibration split (n_fit) and evaluated on test.
5. Every test metric in metrics.json (syndrome, species, calibration) is regenerated from the
   saved predictions file to within 1e-9.
Exit code 1 if any check fails. Results on simulated data are SIMULATION results.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from src.artifacts import git_state
from src.data.dataset import load_dataset, validation_split
from src.data.splits import check_disjoint
from src.evaluate import evaluate_predictions

TOL = 1e-9


def _close(a: Any, b: Any) -> bool:
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return abs(float(a) - float(b)) <= TOL


def compare(saved: dict[str, Any], recomputed: dict[str, Any], prefix: str = "") -> list[str]:
    """Paths of scalar metrics that differ (only keys present in both)."""
    bad = []
    for key, value in saved.items():
        if key not in recomputed:
            continue
        other = recomputed[key]
        if isinstance(value, dict) and isinstance(other, dict):
            bad += compare(value, other, f"{prefix}{key}.")
        elif isinstance(value, (int, float)) and not isinstance(value, bool) and isinstance(other, (int, float)):
            if not _close(value, other):
                bad.append(f"{prefix}{key}: {value} vs {other}")
    return bad


def verify_run(run_dir: Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    info = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    ds = load_dataset(info["config"]["dataset"])
    head = git_state()
    problems: list[str] = []
    if info.get("status") != "complete":
        problems.append(f"run status is {info.get('status')!r}")
    recorded = (info.get("git") or {}).get("commit") or str(info.get("git_commit", "")).removesuffix("-dirty")
    commit_matches = recorded == head["commit"]
    split_of = dict(zip(ds.patients["patient_id"], ds.patients["split"]))
    label_of = dict(zip(ds.patients["patient_id"], ds.syndrome_index))
    train = ds.split_mask("train")
    n_checked = 0
    for name, res in metrics.items():
        for r in res["runs"]:
            seed = int(r["seed"])
            fit, val = validation_split(train, float(info["config"].get("validation_fraction", 0.15)), seed)
            try:
                check_disjoint({"fit": fit, "validation": val, "calibration": ds.split_mask("calibration"),
                                "test": ds.split_mask("test")})
            except ValueError as err:
                problems.append(f"{name} seed {seed}: {err}")
            if (fit | val).sum() != train.sum() or not train[fit | val].all():
                problems.append(f"{name} seed {seed}: fit/validation not exactly the train split")
            path = run_dir / f"predictions_{name}_seed{seed}.npz"
            data = np.load(path)
            ids, splits = data["patient_id"], data["split"]
            if set(splits) - {"calibration", "test"}:
                problems.append(f"{path.name}: contains splits {sorted(set(splits))}")
            if any(split_of[int(i)] != s for i, s in zip(ids, splits)):
                problems.append(f"{path.name}: a patient's saved split differs from the dataset")
            if any(label_of[int(i)] != y for i, y in zip(ids, data["y_syndrome"])):
                problems.append(f"{path.name}: saved labels differ from the dataset")
            if "calibration" in r:
                n_cal, n_test = int((splits == "calibration").sum()), int((splits == "test").sum())
                if r["calibration"]["n_fit"] != n_cal or r["calibration"]["n_eval"] != n_test:
                    problems.append(f"{path.name}: calibration fitted/evaluated on unexpected rows")
            recomputed = evaluate_predictions(path)
            diffs = compare(r["metrics"], recomputed)
            if "calibration" in r and "calibration" in recomputed:
                diffs += compare({k: r["calibration"][k] for k in ("syndrome", "envenomed")},
                                 recomputed["calibration"], "calibration.")
            problems += [f"{path.name}: {d}" for d in diffs]
            n_checked += 1
    return {"run": str(run_dir), "status": info.get("status"), "recorded_commit": recorded,
            "recorded_dirty": (info.get("git") or {}).get("dirty"), "head_commit": head["commit"],
            "head_dirty": head["dirty"], "commit_matches_head": commit_matches,
            "prediction_files_checked": n_checked, "problems": problems}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", nargs="+")
    args = parser.parse_args(argv)
    results = [verify_run(Path(r)) for r in args.runs]
    print(json.dumps(results, indent=2))
    return 1 if any(r["problems"] or not r["commit_matches_head"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
