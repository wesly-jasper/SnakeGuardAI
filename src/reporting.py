"""Markdown reports for Phase 2 runs (train, ablation, robustness). SIMULATION results only."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.data.simulator import SYNDROMES
from src.decision_policy import DISCLAIMER

HEADER = "> **SIMULATION RESULTS** on synthetic patients from a literature-derived table. Not clinical evidence.\n"
RESEARCH_ONLY = ("> Research prototype, not a medical device. Nothing here is a clinical decision rule "
                 "or a validated threshold.\n")


def fmt(cell: dict[str, float] | None, digits: int = 3) -> str:
    """'mean ± sd' (sd omitted when 0), '-' when missing, 'n/a' when NaN."""
    if cell is None:
        return "-"
    mean, sd = cell["mean"], cell["sd"]
    if mean is None or (isinstance(mean, float) and np.isnan(mean)):
        return "n/a"
    return f"{mean:.{digits}f} ± {sd:.{digits}f}" if sd else f"{mean:.{digits}f}"


def table(rows: list[dict[str, Any]]) -> str:
    return pd.DataFrame(rows).to_markdown(index=False) if rows else "(none)"


def syndrome_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, res in results.items():
        s = res["summary"]["syndrome"]
        rows.append({
            "model": name, "seeds": len(res["runs"]), "macro_f1": fmt(s["macro_f1"]),
            "weighted_f1": fmt(s.get("weighted_f1")), "accuracy": fmt(s["accuracy"]),
            "critical_error": fmt(s["critical_error_rate"]),
            "env_sensitivity": fmt(s.get("envenomation_sensitivity")),
            "env_specificity": fmt(s.get("envenomation_specificity")),
            "nll": fmt(s.get("nll")), "ece": fmt(s.get("ece")), "brier": fmt(s.get("brier")),
        })
    return rows


def per_class_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, res in results.items():
        for label, m in res["summary"]["per_class"].items():
            rows.append({"model": name, "class": label, "precision": fmt(m["precision"]), "recall": fmt(m["recall"]),
                         "f1": fmt(m["f1"]), "specificity": fmt(m["specificity"]), "support": int(m["support"]["mean"])})
    return rows


def critical_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, res in results.items():
        ce = res["summary"]["critical_error"]
        row = {"model": name,
               "missed / envenomed": f"{ce['overall']['numerator']['mean']:.1f} / {ce['overall']['denominator']['mean']:.0f}",
               "rate": fmt(ce["overall"]["rate"])}
        row |= {f"{label}": fmt(v["rate"]) for label, v in ce["by_syndrome"].items()}
        for group in ("no_observed_symptom", "any_observed_symptom"):
            if group in ce:
                g = ce[group]
                row[group] = f"{fmt(g['rate'])} ({g['numerator']['mean']:.1f}/{g['denominator']['mean']:.0f})"
        rows.append(row)
    return rows


def policy_rows(results: dict[str, Any], group: str) -> list[dict[str, Any]]:
    rows = []
    for name, res in results.items():
        for row in res["summary"].get("decision_policy", {}).get(group, []):
            rows.append({
                "model": name, "threshold": f"{row['threshold']['mean']:g}",
                "referred": f"{row['n_referred']['mean']:.0f}", "low_risk": f"{row['n_low_risk']['mean']:.0f}",
                "envenomed_low_risk": f"{row['n_envenomed_low_risk']['mean']:.1f}",
                "sensitivity": fmt(row["sensitivity"]), "specificity": fmt(row["specificity"]),
                "npv": fmt(row["npv"]), "ppv": fmt(row["ppv"]), "referral_rate": fmt(row["referral_rate"]),
                "critical_error": fmt(row["critical_error_rate"]),
            })
    return rows


def render_train_report(results: dict[str, Any], n_test: int, n_no_obs: int, run_info: dict[str, Any]) -> str:
    config = run_info["config"]
    species_rows, strat_rows, feature_rows, confusions = [], [], [], []
    for name, res in results.items():
        s = res["summary"]
        if "species" in s:
            sp = s["species"]
            species_rows.append({"model": name, "accuracy": fmt(sp["accuracy"]), "macro_f1": fmt(sp["macro_f1"]),
                                 "top3_accuracy": fmt(sp["top3_accuracy"]), "nll": fmt(sp["nll"])})
        for group, m in s["stratified"].items():
            strat_rows.append({"model": name, "group": group, "n": int(m["n"]["mean"]), "macro_f1": fmt(m["macro_f1"]),
                               "accuracy": fmt(m["accuracy"]), "critical_error": fmt(m["critical_error_rate"])})
        feats = res.get("features") or []
        feature_rows.append({"model": name, "kind": res.get("kind", name), "n_inputs": len(feats),
                             "inputs": ", ".join(feats) if len(feats) <= 6 else ", ".join(feats[:4]) + f", ... ({len(feats)} total)"})
        matrix = pd.DataFrame(res["runs"][0]["metrics"]["confusion"], index=list(SYNDROMES), columns=list(SYNDROMES))
        matrix.index.name = "true \\ predicted"
        confusions += [f"\n### {name} (seed {res['runs'][0]['seed']})\n", matrix.to_markdown()]
    parts = [
        f"# Phase 2: symptom-only baselines on `{config['dataset']}`\n",
        HEADER if run_info["SIMULATED"] else "",
        RESEARCH_ONLY,
        f"- run `{config['name']}`, commit `{run_info['git_commit']}`; dataset `{run_info['dataset']}` "
        f"({run_info['dataset_experiment_type']}, generated at `{run_info['dataset_git_commit']}`)",
        f"- test split: {n_test} patients, {n_no_obs} ({n_no_obs / max(1, n_test):.0%}) with no symptom observed by presentation",
        f"- learned models: train split minus a {config.get('validation_fraction', 0.15):.0%} validation subset "
        f"(early stopping); seeds {config['seeds']}; mean ± sd over training seeds (one simulated dataset). "
        "The calibration split is not used. Hyperparameters are fixed in the config; none is tuned.",
        "- inputs pass the allowlist in `src/data/features.py` (observed symptoms, onset times, presentation time, "
        "optional hour/indoor/asleep). GPS and month are placeholders and never used.",
        "\n## Venom syndrome (test split)\n",
        table(syndrome_rows(results)),
        "\nCritical error = share of envenomed patients predicted non-venomous/dry (lower is better), at the argmax. "
        "env_sensitivity = 1 - critical error; env_specificity = share of non-envenomed predicted non-venomous/dry.",
        "\n## Per-class metrics (test split, one-vs-rest)\n",
        table(per_class_rows(results)),
        "\n## Critical error breakdown (test split)\n",
        table(critical_rows(results)),
        "\nPer-syndrome columns: share of patients with that true syndrome predicted non-venomous/dry.",
        "\n## Species (test split)\n",
        table(species_rows),
        "\n## Syndrome by what was observed at presentation (test split)\n",
        table(strat_rows),
        "\n## Experimental threshold policy on P(envenomed) (test split, all patients)\n",
        f"> {DISCLAIMER}\n",
        "Refer if P(envenomed) = 1 - P(non-venomous/dry) >= threshold; otherwise 'low risk'. Thresholds are "
        "listed, not selected.\n",
        table(policy_rows(results, "all")),
        "\n## Experimental threshold policy, patients with no observed symptom (test split)\n",
        table(policy_rows(results, "no_observed_symptom")),
        "\n## Model inputs (validated against the allowlist)\n",
        table(feature_rows),
        "\n## Syndrome confusion matrices (test split)\n",
        *confusions,
    ]
    return "\n".join(parts) + "\n"
