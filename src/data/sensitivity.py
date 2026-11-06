"""Sensitivity analysis: regenerate the simulated dataset under alternative assumptions.

    python -m src.data.sensitivity --config configs/sensitivity_v2.yaml

Each variant applies config changes (`set`) and single-value knowledge changes
(`knowledge_overrides`, see src.data.knowledge.apply_overrides) to the base config and is
run once per seed in `seeds` (default: the base config's seed). Every variant is generated
with `experiment_type: sensitivity`. A variant's `basis` says what it rests on:
`evidence` (base cited values), `cited-alternative` (a different cited value) or
`assumption` (an uncited modelling choice, e.g. the onset fallback window).

Outputs in <output_dir>/:
- per_seed.csv   one row per (variant, seed)
- summary.csv/md mean and 95% t-interval across seeds for each metric
Datasets are written to <output_dir>/<variant>/seed_<seed>/; the patient and event CSVs are
kept for the first seed only unless `keep_all_datasets: true`.
All numbers are SIMULATION results; the intervals cover simulation and test-split
sampling variability only, not uncertainty in the knowledge table.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy import stats

from src.data.generate import SENSITIVITY, generate, load_config, resolve
from src.data.simulator import SYNDROMES

METRICS = ("accuracy", "macro_f1", "critical_error_rate")
BASES = frozenset({"evidence", "cited-alternative", "assumption"})


def variant_config(base: dict[str, Any], variant: dict[str, Any], output_dir: str) -> dict[str, Any]:
    """Base config with the variant's settings, overrides and its own output folder."""
    config = copy.deepcopy(base)
    config.update(copy.deepcopy(variant.get("set", {})))
    overrides = list(config.get("knowledge_overrides") or []) + list(variant.get("knowledge_overrides", []))
    config["knowledge_overrides"] = overrides
    config["experiment_type"] = SENSITIVITY
    config["name"] = f"{base['name']}__{variant['name']}"
    config["output_dir"] = str(Path(output_dir) / variant["name"])
    return config


def summarise(meta: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    counts = meta["syndrome_counts"]
    total = sum(counts.values()) or 1
    row: dict[str, Any] = {"variant": variant["name"], "description": variant.get("description", "")}
    row.update({f"%{s}": 100 * counts.get(s, 0) / total for s in SYNDROMES})
    row.update({k: v for k, v in meta["rule_baseline_test"].items() if k != "n"})
    return row


def t_interval(values: pd.Series, level: float = 0.95) -> tuple[float, float, float]:
    """(mean, low, high) of a t-interval for the mean; (mean, nan, nan) for one value."""
    x = values.dropna().to_numpy(dtype=float)
    mean = float(x.mean()) if len(x) else float("nan")
    if len(x) < 2:
        return mean, float("nan"), float("nan")
    half = stats.t.ppf(0.5 + level / 2, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return mean, mean - half, mean + half


def aggregate(per_seed: pd.DataFrame) -> pd.DataFrame:
    """Mean and 95% t-interval across seeds for each variant and metric."""
    rows = []
    for name, group in per_seed.groupby("variant", sort=False):
        row: dict[str, Any] = {
            "variant": name, "basis": group["basis"].iloc[0],
            "description": group["description"].iloc[0], "n_seeds": len(group),
        }
        row.update({f"%{s}": group[f"%{s}"].mean() for s in SYNDROMES})
        for metric in METRICS:
            mean, lo, hi = t_interval(group[metric])
            row.update({metric: mean, f"{metric}_ci_low": lo, f"{metric}_ci_high": hi})
        rows.append(row)
    return pd.DataFrame(rows)


def _drop_data_files(out: Path) -> None:
    for name in ("patients.csv", "events.csv"):
        (out / name).unlink(missing_ok=True)


def run(sensitivity: dict[str, Any]) -> pd.DataFrame:
    """Per-(variant, seed) metrics."""
    base = load_config(resolve(sensitivity["base_config"]))
    if "n_patients" in sensitivity:
        base["n_patients"] = sensitivity["n_patients"]
    seeds = [int(s) for s in sensitivity.get("seeds", [base["seed"]])]
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be a non-empty list of distinct integers")
    rows = []
    for variant in sensitivity["variants"]:
        basis = variant.get("basis", "evidence")
        if basis not in BASES:
            raise ValueError(f"variant {variant['name']}: basis must be one of {sorted(BASES)}")
        config = variant_config(base, variant, sensitivity["output_dir"])
        for i, seed in enumerate(seeds):
            out = generate({**config, "seed": seed, "output_dir": str(Path(config["output_dir"]) / f"seed_{seed}")})
            row = summarise(json.loads((out / "meta.json").read_text(encoding="utf-8")), variant)
            rows.append({**row, "basis": basis, "seed": seed})
            if i > 0 and not sensitivity.get("keep_all_datasets", False):
                _drop_data_files(out)
    return pd.DataFrame(rows)


def _ci(row: pd.Series, metric: str) -> str:
    if np.isnan(row[f"{metric}_ci_low"]):
        return f"{row[metric]:.3f}"
    return f"{row[metric]:.3f} [{row[f'{metric}_ci_low']:.3f}, {row[f'{metric}_ci_high']:.3f}]"


def render(summary: pd.DataFrame, sensitivity: dict[str, Any]) -> str:
    table = summary[["variant", "basis", "description", *[f"%{s}" for s in SYNDROMES]]].copy()
    for metric in METRICS:
        table[metric] = summary.apply(_ci, axis=1, metric=metric)
    seeds = sensitivity.get("seeds", ["base config seed"])
    spread = summary[["critical_error_rate", "macro_f1"]].agg(["min", "max"])
    return "\n".join([
        "# Sensitivity analysis",
        "",
        "> **SIMULATION RESULTS.** Rule-based syndromic baseline on each variant's test split.",
        "> Not clinical validation. Intervals are 95% t-intervals across seeds and cover only",
        "> simulation and split variability, not uncertainty in the cited values.",
        "",
        f"Base config `{sensitivity['base_config']}`, {sensitivity.get('n_patients', 'config')} patients "
        f"per run, seeds {seeds}. `basis`: evidence = base cited values; cited-alternative = another "
        "cited value; assumption = uncited modelling choice.",
        "",
        table.to_markdown(index=False, floatfmt=".1f"),
        "",
        f"Mean critical error rate ranges {spread.loc['min', 'critical_error_rate']:.3f}-"
        f"{spread.loc['max', 'critical_error_rate']:.3f}; mean macro-F1 ranges "
        f"{spread.loc['min', 'macro_f1']:.3f}-{spread.loc['max', 'macro_f1']:.3f} across variants.",
        "",
    ])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    sensitivity = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    per_seed = run(sensitivity)
    summary = aggregate(per_seed)
    out = resolve(sensitivity["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    per_seed.to_csv(out / "per_seed.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    (out / "summary.md").write_text(render(summary, sensitivity), encoding="utf-8")
    print(render(summary, sensitivity))


if __name__ == "__main__":
    main()
