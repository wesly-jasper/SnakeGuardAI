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
once per seed. The `calibration` split is never used to fit or select models; it only fits
post-hoc calibrators (temperature, Platt, isotonic; src/uncertainty/calibration.py), and its
probabilities are saved for the Phase 6 conformal gate. Metrics are on the `test` split,
raw and calibrated, including research-only threshold tables for P(envenomed) on the raw
probabilities (src/decision_policy.py).

Writes to `output_dir`: metrics.json, report.md, run.json (status, run id, config, git commit
and dirty flag, simulator and model seeds, dataset and knowledge hashes, feature allowlist and
every model's input columns, split distributions, calibration settings, package versions),
attempts.jsonl (every attempt, including failures), predictions_<model>_seed<k>.npz (raw and
calibrated, calibration and test splits only) and reliability_<model>_seed<k>.png when
matplotlib is installed. A completed run is not overwritten without `--overwrite`.
All results on simulated data are SIMULATION results.
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

from src.artifacts import RunRecorder, base_info
from src.data.dataset import SymptomDataset, load_dataset, resolve, validation_split
from src.data.features import (
    ALLOWED_CONTEXT_COLUMNS,
    ALLOWED_INPUT_COLUMNS,
    FORBIDDEN_COLUMNS,
    FORBIDDEN_PREFIXES,
    ModelInputs,
    build_inputs,
    tabular_matrix,
)
from src.data.splits import check_disjoint, split_summary
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
from src.uncertainty.calibration import METHODS, evaluate_calibration, plot_reliability

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
    check_disjoint({"fit": fit_mask, "validation": val_mask, "calibration": ds.split_mask("calibration"),
                    "test": ds.split_mask("test")})
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


def save_predictions(
    path: Path, ds: SymptomDataset, n_observed: np.ndarray, prediction: Prediction,
    calibrated: dict[str, np.ndarray] | None = None,
) -> None:
    """Raw (and, if given, calibrated) predictions for the calibration and test splits."""
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
    for key, value in (calibrated or {}).items():
        arrays[key] = value[keep]
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
    if "calibration" in runs[0]:
        summary["calibration"] = summarise_calibration([r["calibration"] for r in runs])
    return summary


def summarise_calibration(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean and sd over seeds of raw / calibrated NLL, Brier and ECE, and how often each method helped."""
    out: dict[str, Any] = {"skipped": reports[0]["skipped"]}
    for target in ("syndrome", "envenomed"):
        out[target] = {
            method: {k: _mean_sd([r[target][method][k] for r in reports]) for k in ("nll", "brier", "ece")}
            | ({"helps_nll_seeds": sum(bool(r[target][method]["helps_nll"]) for r in reports)}
               if method != "raw" else {})
            for method in reports[0][target]
        }
    return out


def calibration_settings(config: dict[str, Any]) -> dict[str, Any]:
    settings = {"methods": list(METHODS), "min_isotonic_n": 1000, "min_isotonic_class": 50,
                **(config.get("calibration") or {})}
    unknown = set(settings["methods"]) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown calibration methods {sorted(unknown)}; expected {METHODS}")
    return settings


def run(config: dict[str, Any], overwrite: bool = False) -> Path:
    ds = load_dataset(config["dataset"])
    inputs = build_inputs(ds)
    n_observed = inputs.n_observed
    test = ds.split_mask("test")
    thresholds = validate_thresholds(config.get("decision_thresholds", DEFAULT_THRESHOLDS))
    calibration = calibration_settings(config)
    out = resolve(config["output_dir"])
    torch.set_num_threads(int(config.get("torch_threads", 4)))
    validation_fraction = float(config.get("validation_fraction", 0.15))
    info = base_info(config, resolve(config["dataset"]), ds.meta) | {
        "feature_allowlist": {
            "input_columns": sorted(ALLOWED_INPUT_COLUMNS), "context_columns": sorted(ALLOWED_CONTEXT_COLUMNS),
            "forbidden_columns": sorted(FORBIDDEN_COLUMNS), "forbidden_prefixes": list(FORBIDDEN_PREFIXES),
        },
        "splits": split_summary(ds.patients, tabular_matrix(inputs)[0]),
        "split_assignment": ds.meta.get("split_assignment", {"strategy": "random"}),
        "validation_fraction": validation_fraction,
        "decision_thresholds": thresholds,
        "calibration": calibration | {"fitted_on": "calibration split only; evaluated on test"},
    }
    with RunRecorder(out, info, overwrite or bool(config.get("overwrite", False))) as recorder:
        results = train_models(config, ds, inputs, out, thresholds, calibration, validation_fraction)
        recorder.info["model_inputs"] = {name: res["features"] for name, res in results.items()}
        (out / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        report = render_train_report(results, int(test.sum()), int((n_observed[test] == 0).sum()), recorder.info)
        (out / "report.md").write_text(report, encoding="utf-8")
        recorder.info["artifacts"] = sorted(p.name for p in out.iterdir() if p.name not in {"run.json", "attempts.jsonl"})
    return out


def train_models(
    config: dict[str, Any], ds: SymptomDataset, inputs: ModelInputs, out: Path, thresholds: list[float],
    calibration: dict[str, Any], validation_fraction: float,
) -> dict[str, Any]:
    """Fit, predict, evaluate and calibrate every configured model for every seed."""
    n_observed = inputs.n_observed
    test, cal = ds.split_mask("test"), ds.split_mask("calibration")
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
            record: dict[str, Any] = {"seed": seed, "seconds": round(time.perf_counter() - start, 1),
                                      "info": getattr(model, "info", {}), "metrics": metrics}
            calibrated = None
            if prediction.p_syndrome is not None and calibration["methods"]:
                record["calibration"], calibrated = evaluate_calibration(
                    prediction.p_syndrome, ds.syndrome_index, cal, test, tuple(calibration["methods"]),
                    int(calibration["min_isotonic_n"]), int(calibration["min_isotonic_class"]),
                )
                if seed == seeds[0]:
                    plot_reliability(record["calibration"], out / f"reliability_{name}_seed{seed}.png",
                                     f"{name}, seed {seed}, test split")
            runs.append(record)
            features = model.feature_names
            save_predictions(out / f"predictions_{name}_seed{seed}.npz", ds, n_observed, prediction, calibrated)
            print(f"{name} seed {seed}: syndrome macro-F1 {metrics['syndrome']['macro_f1']:.3f}, "
                  f"critical error {metrics['syndrome']['critical_error_rate']:.3f}")
        results[name] = {"kind": spec.kind, "features": features, "feature_spec": asdict(spec.features),
                         "runs": runs, "summary": summarise(runs)}
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    parser.add_argument("--overwrite", action="store_true", help="replace a completed run in output_dir")
    args = parser.parse_args(argv)
    out = run(load_config(args.config), overwrite=args.overwrite)
    print(f"wrote results to {out}")


if __name__ == "__main__":
    main()
