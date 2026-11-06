"""Phase 2: train and evaluate the symptom-only baselines on a simulated dataset.

    python -m src.train --config configs/phase2_sim_v2.yaml

Models (all see only what is known at presentation, through the input allowlist in
src/data/features.py: observed symptoms with onset times, presentation time and, where a
model asks for it, hour of day / indoor / asleep):
- `prior`: training-set class frequencies (floor).
- `rule`: the rule-based syndromic table applied to observed symptoms (from Phase 1).
- `xgboost`: symptom-only XGBoost, one classifier per head.
- `xgboost_context`: the same plus context (reference only; context fusion proper is Phase 5).
- `logistic_regression`, `random_forest`: conventional baselines (src/models/sklearn_baselines.py).
- `transformer`: the symptom transformer (src/models/symptom_transformer.py).

Learned models train on the `train` split (minus a validation subset for early stopping),
once per seed. The `calibration` split is never used for fitting or selection; its
probabilities are saved for the Phase 6 conformal gate. Metrics are on the `test` split,
including research-only threshold tables for P(envenomed) (src/decision_policy.py).

Writes to `output_dir`: metrics.json, report.md, run.json (config, git commit, dataset
meta, every model's input features) and predictions_<model>_seed<k>.npz. All results on
simulated data are SIMULATION results.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

from src.data.dataset import SymptomDataset, load_dataset, resolve, validation_split
from src.data.features import ModelInputs, build_inputs
from src.data.generate import git_commit
from src.data.simulator import DEFAULT_PRECEDENCE, SYNDROMES
from src.decision_policy import DEFAULT_THRESHOLDS, policy_evaluation, validate_thresholds
from src.evaluate import (
    confusion,
    critical_error_detail,
    per_class_metrics,
    species_metrics,
    stratified_syndrome,
    syndrome_metrics,
)
from src.models.registry import FittedModel, ModelSpec, Prediction, fit_model, resolve_model
from src.reporting import render_train_report

SAVED_SPLITS = ("calibration", "test")


def load_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key in ("name", "dataset", "output_dir", "seeds", "models"):
        if key not in config:
            raise ValueError(f"config missing required key: {key}")
    for name, entry in config["models"].items():
        resolve_model(name, entry)  # raises on unknown models or options
    validate_thresholds(config.get("decision_thresholds", DEFAULT_THRESHOLDS))
    return config


def precedence_of(ds: SymptomDataset) -> tuple[str, ...]:
    return tuple(ds.meta["config"].get("syndrome_precedence", DEFAULT_PRECEDENCE))


def fit_for_seed(
    spec: ModelSpec, ds: SymptomDataset, inputs: ModelInputs, seed: int, validation_fraction: float,
) -> FittedModel:
    """Fit on the train split minus a seeded validation subset; calibration/test never touched."""
    fit_mask, val_mask = validation_split(ds.split_mask("train"), validation_fraction, seed)
    return fit_model(
        spec, inputs, ds.syndrome_index, ds.species_index, np.flatnonzero(fit_mask), np.flatnonzero(val_mask),
        int(seed), len(ds.species), precedence_of(ds),
    )


def evaluate_run(
    y_syndrome: np.ndarray, y_species: np.ndarray, n_observed: np.ndarray, prediction: Prediction,
    mask: np.ndarray, thresholds: list[float],
) -> dict[str, Any]:
    """All metrics on the patients in `mask` (the test split)."""
    y_syn, y_sp, n_obs = y_syndrome[mask], y_species[mask], n_observed[mask]
    pred = prediction.pred_syndrome[mask]
    p_syn = None if prediction.p_syndrome is None else prediction.p_syndrome[mask]
    out: dict[str, Any] = {
        "syndrome": syndrome_metrics(y_syn, pred, p_syn),
        "stratified": stratified_syndrome(y_syn, pred, n_obs),
        "confusion": confusion(y_syn, pred, len(SYNDROMES)).tolist(),
        "per_class": per_class_metrics(y_syn, pred),
        "critical_error": critical_error_detail(y_syn, pred, n_obs),
    }
    if p_syn is not None:
        out["decision_policy"] = policy_evaluation(y_syn, p_syn, n_obs, thresholds)
    if prediction.p_species is not None:
        out["species"] = species_metrics(y_sp, prediction.p_species[mask])
    return out


def save_predictions(path: Path, ds: SymptomDataset, n_observed: np.ndarray, prediction: Prediction) -> None:
    keep = ds.patients["split"].isin(SAVED_SPLITS).to_numpy()
    arrays: dict[str, np.ndarray] = {
        "patient_id": ds.patients["patient_id"].to_numpy()[keep],
        "split": ds.patients["split"].to_numpy().astype(str)[keep],
        "y_syndrome": ds.syndrome_index[keep],
        "y_species": ds.species_index[keep],
        "pred_syndrome": prediction.pred_syndrome[keep],
        "n_observed": n_observed[keep],
        "syndrome_labels": np.array(SYNDROMES),
        "species_labels": np.array(ds.species),
    }
    if prediction.p_syndrome is not None:
        arrays["p_syndrome"] = prediction.p_syndrome[keep]
    if prediction.p_species is not None:
        arrays["p_species"] = prediction.p_species[keep]
    np.savez_compressed(path, **arrays)


def _mean_sd(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    if np.isnan(arr).all():
        return {"mean": float("nan"), "sd": float("nan")}
    return {"mean": float(np.nanmean(arr)), "sd": float(np.nanstd(arr))}


def summarise(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean and sd over seeds of every scalar metric (NaN-aware)."""
    first = runs[0]["metrics"]
    summary: dict[str, Any] = {}
    for head in ("syndrome", "species"):
        if head in first:
            summary[head] = {k: _mean_sd([r["metrics"][head][k] for r in runs]) for k in first[head] if k != "n"}
    summary["stratified"] = {
        group: {k: _mean_sd([r["metrics"]["stratified"][group][k] for r in runs]) for k in values if k != "n"}
        | {"n": {"mean": values["n"], "sd": 0.0}}
        for group, values in first["stratified"].items()
    }
    summary["per_class"] = {
        label: {k: _mean_sd([r["metrics"]["per_class"][label][k] for r in runs]) for k in values}
        for label, values in first["per_class"].items()
    }
    def counts(get) -> dict[str, dict[str, float]]:
        return {k: _mean_sd([get(r["metrics"]["critical_error"])[k] for r in runs]) for k in ("numerator", "denominator", "rate")}

    ce = first["critical_error"]
    summary["critical_error"] = {
        "overall": counts(lambda c: c),
        "by_syndrome": {label: counts(lambda c, label=label: c["by_syndrome"][label]) for label in ce["by_syndrome"]},
        **{group: counts(lambda c, group=group: c[group])
           for group in ("no_observed_symptom", "any_observed_symptom") if group in ce},
    }
    if "decision_policy" in first:
        summary["decision_policy"] = {
            group: [
                {k: _mean_sd([r["metrics"]["decision_policy"][group][i][k] for r in runs]) for k in row}
                for i, row in enumerate(rows)
            ]
            for group, rows in first["decision_policy"].items()
        }
    return summary


def run(config: dict[str, Any]) -> Path:
    ds = load_dataset(config["dataset"])
    inputs = build_inputs(ds)
    n_observed = inputs.n_observed
    test = ds.split_mask("test")
    thresholds = validate_thresholds(config.get("decision_thresholds", DEFAULT_THRESHOLDS))
    out = resolve(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(int(config.get("torch_threads", 4)))
    validation_fraction = float(config.get("validation_fraction", 0.15))
    results: dict[str, Any] = {}
    for name, entry in config["models"].items():
        spec = resolve_model(name, entry)
        seeds = config["seeds"] if spec.learned else [config["seeds"][0]]
        runs, features = [], None
        for seed in seeds:
            start = time.perf_counter()
            model = fit_for_seed(spec, ds, inputs, int(seed), validation_fraction)
            prediction = model.predict(inputs)
            metrics = evaluate_run(ds.syndrome_index, ds.species_index, n_observed, prediction, test, thresholds)
            runs.append({"seed": seed, "seconds": round(time.perf_counter() - start, 1),
                         "info": getattr(model, "info", {}), "metrics": metrics})
            features = model.feature_names
            save_predictions(out / f"predictions_{name}_seed{seed}.npz", ds, n_observed, prediction)
            print(f"{name} seed {seed}: syndrome macro-F1 {metrics['syndrome']['macro_f1']:.3f}, "
                  f"critical error {metrics['syndrome']['critical_error_rate']:.3f}")
        results[name] = {"kind": spec.kind, "features": features, "feature_spec": asdict(spec.features),
                         "runs": runs, "summary": summarise(runs)}
    run_info = {
        "SIMULATED": bool(ds.meta.get("SIMULATED", False)),
        "config": config,
        "git_commit": git_commit(),
        "dataset": str(config["dataset"]),
        "dataset_git_commit": ds.meta.get("git_commit"),
        "dataset_experiment_type": ds.meta.get("experiment_type"),
        "dataset_knowledge_hashes": ds.meta.get("knowledge_hashes"),
        "torch_version": torch.__version__,
        "model_inputs": {name: res["features"] for name, res in results.items()},
        "decision_thresholds": thresholds,
    }
    (out / "run.json").write_text(json.dumps(run_info, indent=2, default=str), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    report = render_train_report(results, int(test.sum()), int((n_observed[test] == 0).sum()), run_info)
    (out / "report.md").write_text(report, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    out = run(load_config(args.config))
    print(f"wrote results to {out}")


if __name__ == "__main__":
    main()
