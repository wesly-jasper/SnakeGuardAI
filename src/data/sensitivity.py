"""Sensitivity analysis: regenerate the simulated dataset under alternative assumptions.

    python -m src.data.sensitivity --config configs/sensitivity_v1.yaml

Each variant applies config changes (`set`) and single-value knowledge changes
(`knowledge_overrides`, see src.data.knowledge.apply_overrides) to the base config, writes
its dataset to <output_dir>/<variant>/, and the summary table compares syndrome mix and the
rule-based baseline across variants. All numbers are SIMULATION results.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.data.generate import generate, load_config, resolve
from src.data.simulator import SYNDROMES


def variant_config(base: dict[str, Any], variant: dict[str, Any], output_dir: str) -> dict[str, Any]:
    """Base config with the variant's settings, overrides and its own output folder."""
    config = copy.deepcopy(base)
    config.update(copy.deepcopy(variant.get("set", {})))
    overrides = list(config.get("knowledge_overrides") or []) + list(variant.get("knowledge_overrides", []))
    config["knowledge_overrides"] = overrides
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


def run(sensitivity: dict[str, Any]) -> pd.DataFrame:
    base = load_config(resolve(sensitivity["base_config"]))
    if "n_patients" in sensitivity:
        base["n_patients"] = sensitivity["n_patients"]
    rows = []
    for variant in sensitivity["variants"]:
        out = generate(variant_config(base, variant, sensitivity["output_dir"]))
        rows.append(summarise(json.loads((out / "meta.json").read_text(encoding="utf-8")), variant))
    return pd.DataFrame(rows)


def render(summary: pd.DataFrame, sensitivity: dict[str, Any]) -> str:
    spread = summary[["critical_error_rate", "macro_f1"]].agg(["min", "max"])
    return "\n".join([
        "# Sensitivity analysis",
        "",
        "> **SIMULATION RESULTS.** Rule-based syndromic baseline on each variant's test split.",
        "",
        f"Base config `{sensitivity['base_config']}`, {sensitivity.get('n_patients', 'config')} patients per variant.",
        "",
        summary.to_markdown(index=False, floatfmt=".3f"),
        "",
        f"Critical error rate ranges {spread.loc['min', 'critical_error_rate']:.3f}-"
        f"{spread.loc['max', 'critical_error_rate']:.3f}; macro-F1 ranges "
        f"{spread.loc['min', 'macro_f1']:.3f}-{spread.loc['max', 'macro_f1']:.3f} across variants.",
        "",
    ])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    sensitivity = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    summary = run(sensitivity)
    out = resolve(sensitivity["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "summary.csv", index=False)
    (out / "summary.md").write_text(render(summary, sensitivity), encoding="utf-8")
    print(render(summary, sensitivity))


if __name__ == "__main__":
    main()
