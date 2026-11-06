"""Phase 2 input ablations: which inputs carry the signal? SIMULATION results only.

    python -m src.ablation --config configs/phase2_ablation_sim_v2.yaml

One model kind (XGBoost by default: fast and the strongest tabular baseline) is retrained per
experiment with some inputs switched off (src/data/features.py FeatureSpec). The dataset,
labels and splits are never changed; only what the model sees. Experiments:

A full observed-symptom model             B symptom presence only (no onset / elapsed time)
C temporal only (no symptom identity)     D no presentation delay (and so no elapsed time)
E leave one symptom out (each symptom observed at least once in the inputs)
F no local symptoms                       G no systemic symptoms (all non-local markers)
H context only (hour, indoor, asleep)     I symptoms plus context

Patient groups for "no observed symptom" are defined on the full inputs, so they are the same
patients in every experiment. An ablation shows what this model uses on this simulated data;
it is not causal clinical evidence about symptoms.

Writes `output_dir/experiments/<name>/{config.json,metrics.json}`, `ablation.json`,
`run.json` and `report.md`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml

from src.data.dataset import load_dataset, resolve
from src.data.features import FeatureSpec, build_inputs
from src.data.generate import git_commit
from src.data.simulator import SYNDROMES
from src.decision_policy import DEFAULT_THRESHOLDS, validate_thresholds
from src.models.registry import resolve_model
from src.reporting import HEADER, RESEARCH_ONLY, fmt
from src.train import evaluate_run, fit_for_seed, summarise

LEAVE_ONE_OUT_PREFIX = "E_drop_"


def load_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key in ("name", "dataset", "output_dir", "seeds", "model", "experiments"):
        if key not in config:
            raise ValueError(f"config missing required key: {key}")
    for name, features in config["experiments"].items():
        FeatureSpec.from_dict(features)
    return config


def describe(spec: FeatureSpec) -> str:
    """Short human-readable summary of what the model sees."""
    if not spec.symptoms:
        parts = ["no symptoms"]
    elif not spec.symptom_identity:
        parts = ["event times without symptom identity"]
    else:
        parts = [", ".join(n for n, on in (("presence", spec.presence), ("onset", spec.onset),
                                            ("elapsed", spec.elapsed)) if on)]
    if spec.symptoms and spec.presentation:
        parts.append("presentation time")
    elif not spec.presentation:
        parts.append("no presentation time")
    if spec.context:
        parts.append("context")
    if spec.drop_symptoms:
        parts.append("minus " + ", ".join(spec.drop_symptoms))
    if spec.drop_groups:
        parts.append("minus " + ", ".join(f"{g} symptoms" for g in spec.drop_groups))
    return "; ".join(parts)


def expand_experiments(config: dict[str, Any], observed_symptoms: list[str]) -> dict[str, dict[str, Any]]:
    """Configured experiments plus one leave-one-out experiment per observed symptom (E)."""
    experiments = {name: dict(features or {}) for name, features in config["experiments"].items()}
    if config.get("leave_one_out", True):
        for symptom in observed_symptoms:
            experiments[f"{LEAVE_ONE_OUT_PREFIX}{symptom}"] = {"drop_symptoms": [symptom]}
    return experiments


def run(config: dict[str, Any]) -> Path:
    ds = load_dataset(config["dataset"])
    inputs = build_inputs(ds)
    n_observed = inputs.n_observed
    test = ds.split_mask("test")
    thresholds = validate_thresholds(config.get("decision_thresholds", DEFAULT_THRESHOLDS))
    torch.set_num_threads(int(config.get("torch_threads", 4)))
    out = resolve(config["output_dir"])
    (out / "experiments").mkdir(parents=True, exist_ok=True)
    counts = np.bincount(np.concatenate([s[:, 0].astype(int) for s in inputs.sequences] or [np.zeros(0, int)]),
                         minlength=len(inputs.symptoms))
    observed = [s for s, c in zip(inputs.symptoms, counts) if c > 0]
    never = [s for s, c in zip(inputs.symptoms, counts) if c == 0]
    results: dict[str, Any] = {}
    for name, features in expand_experiments(config, observed).items():
        spec = resolve_model(name, {**config["model"], "features": features})
        runs, feature_names = [], []
        for seed in config["seeds"]:
            model = fit_for_seed(spec, ds, inputs, int(seed), float(config.get("validation_fraction", 0.15)))
            metrics = evaluate_run(ds.syndrome_index, ds.species_index, n_observed, model.predict(inputs), test, thresholds)
            runs.append({"seed": seed, "info": getattr(model, "info", {}), "metrics": metrics})
            feature_names = model.feature_names
        entry = {"description": describe(spec.features), "kind": spec.kind, "feature_spec": asdict(spec.features),
                 "features": feature_names, "runs": runs, "summary": summarise(runs)}
        results[name] = entry
        exp_dir = out / "experiments" / name
        exp_dir.mkdir(exist_ok=True)
        (exp_dir / "config.json").write_text(json.dumps(
            {"model": config["model"], "features": features, "feature_spec": entry["feature_spec"],
             "seeds": config["seeds"], "dataset": config["dataset"]}, indent=2), encoding="utf-8")
        (exp_dir / "metrics.json").write_text(json.dumps(entry, indent=2), encoding="utf-8")
        s = entry["summary"]["syndrome"]
        print(f"{name}: macro-F1 {s['macro_f1']['mean']:.3f}, critical error {s['critical_error_rate']['mean']:.3f}")
    run_info = {
        "SIMULATED": bool(ds.meta.get("SIMULATED", False)), "config": config, "git_commit": git_commit(),
        "dataset_git_commit": ds.meta.get("git_commit"), "dataset_experiment_type": ds.meta.get("experiment_type"),
        "symptoms_never_observed_in_inputs": never,
    }
    (out / "run.json").write_text(json.dumps(run_info, indent=2, default=str), encoding="utf-8")
    (out / "ablation.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "report.md").write_text(render(results, run_info, int(test.sum()), int((n_observed[test] == 0).sum())),
                                   encoding="utf-8")
    return out


def row(name: str, entry: dict[str, Any], base: dict[str, Any] | None) -> dict[str, Any]:
    s = entry["summary"]
    syn, ce = s["syndrome"], s["critical_error"]

    def delta(key: str) -> str:
        if base is None:
            return "-"
        return f"{syn[key]['mean'] - base['summary']['syndrome'][key]['mean']:+.3f}"

    out = {"experiment": name, "inputs": entry["description"], "n_features": len(entry["features"]),
           "macro_f1": fmt(syn["macro_f1"]), "Δ macro_f1": delta("macro_f1"),
           "critical_error": fmt(syn["critical_error_rate"]), "Δ critical": delta("critical_error_rate")}
    out |= {f"recall {label}": fmt(s["per_class"][label]["recall"]) for label in SYNDROMES}
    out["critical (no obs)"] = fmt(ce["no_observed_symptom"]["rate"]) if "no_observed_symptom" in ce else "-"
    out["macro_f1 (no obs)"] = fmt(s["stratified"]["no_observed_symptom"]["macro_f1"]) \
        if "no_observed_symptom" in s["stratified"] else "-"
    out |= {"ece": fmt(syn.get("ece")), "nll": fmt(syn.get("nll"))}
    return out


def render(results: dict[str, Any], run_info: dict[str, Any], n_test: int, n_no_obs: int) -> str:
    config = run_info["config"]
    base = results.get(config.get("reference", "A_full"))
    main = [row(n, e, base) for n, e in results.items() if not n.startswith(LEAVE_ONE_OUT_PREFIX)]
    loo = sorted((row(n, e, base) for n, e in results.items() if n.startswith(LEAVE_ONE_OUT_PREFIX)),
                 key=lambda r: float(r["Δ critical"]) if r["Δ critical"] != "-" else 0.0, reverse=True)
    parts = [
        f"# Phase 2 input ablations on `{config['dataset']}`\n",
        HEADER if run_info["SIMULATED"] else "", RESEARCH_ONLY,
        f"- run `{config['name']}`, commit `{run_info['git_commit']}`; model kind `{config['model'].get('kind', 'xgboost')}` "
        f"(syndrome head), seeds {config['seeds']}, mean ± sd over training seeds",
        f"- test split {n_test} patients, {n_no_obs} with no symptom observed at presentation (group fixed on the "
        "full inputs). Dataset, labels and splits are identical in every experiment.",
        f"- Δ columns are relative to `{config.get('reference', 'A_full')}`. An ablation shows what this model uses on "
        "simulated data; it is not causal clinical evidence.",
        f"- symptoms never observed in the inputs (label-only or never before presentation), so no leave-one-out "
        f"experiment: {', '.join(run_info['symptoms_never_observed_in_inputs']) or 'none'}",
        "- C (temporal only): the first "
        f"{FeatureSpec().max_events} observed onset times sorted ascending and their times since onset, NaN-padded; "
        "the model is not told which symptom each time belongs to.",
        "\n## Experiments A-D, F-I (test split)\n",
        pd.DataFrame(main).to_markdown(index=False),
        "\n## E: leave one symptom out (test split, sorted by Δ critical error)\n",
        pd.DataFrame(loo).to_markdown(index=False) if loo else "(none)",
    ]
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    print(f"wrote results to {run(load_config(args.config))}")


if __name__ == "__main__":
    main()
