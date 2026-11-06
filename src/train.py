"""Phase 2: train and evaluate the symptom-only baselines on a simulated dataset.

    python -m src.train --config configs/phase2_sim_v2.yaml

Models (all see only the symptoms observed by presentation, plus presentation time):
- `prior`: training-set class frequencies (floor).
- `rule`: the rule-based syndromic table applied to observed symptoms (from Phase 1).
- `xgboost`: symptom-only XGBoost, one classifier per head.
- `xgboost_context`: the same plus hour of day / indoor / asleep (reference only; context
  fusion proper is Phase 5).
- `transformer`: the symptom transformer (src/models/symptom_transformer.py).

Learned models train on the `train` split (minus a validation subset for early stopping),
once per seed. The `calibration` split is never used for fitting; its probabilities are
saved for the Phase 6 conformal gate. Metrics are on the `test` split.

Writes to `output_dir`: metrics.json, report.md, run.json (config, git commit, dataset
meta) and predictions_<model>_seed<k>.npz. All results on simulated data are
SIMULATION results.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml

from src.data.dataset import SymptomDataset, load_dataset, resolve, tabular_features, validation_split
from src.data.generate import git_commit
from src.data.simulator import DEFAULT_PRECEDENCE, SYNDROMES, derive_syndrome
from src.evaluate import confusion, species_metrics, stratified_syndrome, syndrome_metrics
from src.models.trainer import fit_transformer, predict_proba
from src.models.xgb_baseline import XGBHead

HEADER = "> **SIMULATION RESULTS** on synthetic patients from a literature-derived table. Not clinical evidence.\n"
LEARNED = ("xgboost", "xgboost_context", "transformer")
SAVED_SPLITS = ("calibration", "test")


def load_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key in ("name", "dataset", "output_dir", "seeds", "models"):
        if key not in config:
            raise ValueError(f"config missing required key: {key}")
    unknown = set(config["models"]) - {"prior", "rule", *LEARNED}
    if unknown:
        raise ValueError(f"unknown models: {sorted(unknown)}")
    return config


def rule_predictions(ds: SymptomDataset, precedence: tuple[str, ...]) -> np.ndarray:
    """Phase 1 syndromic rule on observed symptoms; the species is unknown, so any symptom counts."""
    markers = pd.read_csv(resolve(ds.meta["config"].get("knowledge_dir", "knowledge")) / "symptoms.csv")
    marker_of = dict(zip(markers["symptom"], markers["marker"]))
    labels = [
        derive_syndrome((ds.symptoms[int(i)] for i in seq[:, 0]), marker_of, True, precedence)
        for seq in ds.sequences
    ]
    return np.array([SYNDROMES.index(label) for label in labels])


def prior_proba(y: np.ndarray, n_classes: int, n: int) -> np.ndarray:
    freq = np.bincount(y, minlength=n_classes) / len(y)
    return np.tile(freq, (n, 1))


def fit_predict(
    name: str, ds: SymptomDataset, params: dict[str, Any], seed: int, fit_idx: np.ndarray, val_idx: np.ndarray,
    precedence: tuple[str, ...],
) -> tuple[np.ndarray | None, np.ndarray, np.ndarray | None, dict[str, Any]]:
    """(syndrome proba or None, syndrome prediction, species proba or None, info) for every patient."""
    y_syn, y_sp = ds.syndrome_index, ds.species_index
    n = len(ds.sequences)
    if name == "prior":
        p_syn = prior_proba(y_syn[fit_idx], len(SYNDROMES), n)
        p_sp = prior_proba(y_sp[fit_idx], len(ds.species), n)
        return p_syn, p_syn.argmax(1), p_sp, {}
    if name == "rule":
        return None, rule_predictions(ds, precedence), None, {}
    if name in ("xgboost", "xgboost_context"):
        x, _ = tabular_features(ds, use_context=name == "xgboost_context")
        heads = {}
        for head, y, k in (("syndrome", y_syn, len(SYNDROMES)), ("species", y_sp, len(ds.species))):
            heads[head] = XGBHead(k, params.get("params", {}), seed).fit(x[fit_idx], y[fit_idx], x[val_idx], y[val_idx])
        p_syn, p_sp = heads["syndrome"].predict_proba(x), heads["species"].predict_proba(x)
        info = {f"{h}_best_iteration": int(m.model.best_iteration) for h, m in heads.items()}
        return p_syn, p_syn.argmax(1), p_sp, info
    if name == "transformer":
        presentation = ds.patients["presentation_hours"].to_numpy(dtype=float)
        result = fit_transformer(
            ds.sequences, presentation, y_syn, y_sp, fit_idx, val_idx,
            len(ds.symptoms), len(SYNDROMES), len(ds.species), params, seed,
        )
        p_syn, p_sp = predict_proba(result.model, ds.sequences, presentation, np.arange(n))
        info = {"best_epoch": result.best_epoch, "epochs_run": len(result.history),
                "final_val_loss": min(h["val_loss"] for h in result.history)}
        return p_syn, p_syn.argmax(1), p_sp, info
    raise ValueError(name)


def evaluate_run(
    ds: SymptomDataset, p_syn: np.ndarray | None, pred: np.ndarray, p_sp: np.ndarray | None,
) -> dict[str, Any]:
    test = ds.split_mask("test")
    y_syn, y_sp = ds.syndrome_index[test], ds.species_index[test]
    n_obs = np.array([len(s) for s in ds.sequences])[test]
    out: dict[str, Any] = {
        "syndrome": syndrome_metrics(y_syn, pred[test], None if p_syn is None else p_syn[test]),
        "stratified": stratified_syndrome(y_syn, pred[test], n_obs),
        "confusion": confusion(y_syn, pred[test], len(SYNDROMES)).tolist(),
    }
    if p_sp is not None:
        out["species"] = species_metrics(y_sp, p_sp[test])
    return out


def save_predictions(
    path: Path, ds: SymptomDataset, p_syn: np.ndarray | None, pred: np.ndarray, p_sp: np.ndarray | None,
) -> None:
    keep = ds.patients["split"].isin(SAVED_SPLITS).to_numpy()
    arrays: dict[str, np.ndarray] = {
        "patient_id": ds.patients["patient_id"].to_numpy()[keep],
        "split": ds.patients["split"].to_numpy().astype(str)[keep],
        "y_syndrome": ds.syndrome_index[keep],
        "y_species": ds.species_index[keep],
        "pred_syndrome": pred[keep],
        "n_observed": np.array([len(s) for s in ds.sequences])[keep],
        "syndrome_labels": np.array(SYNDROMES),
        "species_labels": np.array(ds.species),
    }
    if p_syn is not None:
        arrays["p_syndrome"] = p_syn[keep]
    if p_sp is not None:
        arrays["p_species"] = p_sp[keep]
    np.savez_compressed(path, **arrays)


def summarise(runs: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float]]]:
    """Mean and sd over seeds of every scalar metric, per head."""
    summary: dict[str, dict[str, dict[str, float]]] = {}
    for head in ("syndrome", "species"):
        if head not in runs[0]["metrics"]:
            continue
        keys = [k for k in runs[0]["metrics"][head] if k != "n"]
        summary[head] = {
            k: {"mean": float(np.mean(v := [r["metrics"][head][k] for r in runs])), "sd": float(np.std(v, ddof=0))}
            for k in keys
        }
    strata = runs[0]["metrics"]["stratified"]
    summary["stratified"] = {
        group: {k: {"mean": float(np.mean(v := [r["metrics"]["stratified"][group][k] for r in runs])),
                    "sd": float(np.std(v))} for k in strata[group] if k != "n"} | {"n": {"mean": strata[group]["n"], "sd": 0.0}}
        for group in strata
    }
    return summary


def run(config: dict[str, Any]) -> Path:
    ds = load_dataset(config["dataset"])
    out = resolve(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    precedence = tuple(ds.meta["config"].get("syndrome_precedence", DEFAULT_PRECEDENCE))
    torch.set_num_threads(int(config.get("torch_threads", 4)))
    results: dict[str, Any] = {}
    for name, params in config["models"].items():
        params = params or {}
        seeds = config["seeds"] if name in LEARNED else [config["seeds"][0]]
        runs = []
        for seed in seeds:
            fit_mask, val_mask = validation_split(ds.split_mask("train"), float(config.get("validation_fraction", 0.15)), seed)
            start = time.perf_counter()
            p_syn, pred, p_sp, info = fit_predict(
                name, ds, params, int(seed), np.flatnonzero(fit_mask), np.flatnonzero(val_mask), precedence,
            )
            metrics = evaluate_run(ds, p_syn, pred, p_sp)
            runs.append({"seed": seed, "seconds": round(time.perf_counter() - start, 1), "info": info, "metrics": metrics})
            save_predictions(out / f"predictions_{name}_seed{seed}.npz", ds, p_syn, pred, p_sp)
            print(f"{name} seed {seed}: syndrome macro-F1 {metrics['syndrome']['macro_f1']:.3f}, "
                  f"critical error {metrics['syndrome']['critical_error_rate']:.3f}")
        results[name] = {"runs": runs, "summary": summarise(runs)}
    run_info = {
        "SIMULATED": bool(ds.meta.get("SIMULATED", False)),
        "config": config,
        "git_commit": git_commit(),
        "dataset": str(config["dataset"]),
        "dataset_git_commit": ds.meta.get("git_commit"),
        "dataset_experiment_type": ds.meta.get("experiment_type"),
        "dataset_knowledge_hashes": ds.meta.get("knowledge_hashes"),
        "torch_version": torch.__version__,
    }
    (out / "run.json").write_text(json.dumps(run_info, indent=2, default=str), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "report.md").write_text(render_report(results, ds, run_info), encoding="utf-8")
    return out


def _fmt(cell: dict[str, float] | None, digits: int = 3) -> str:
    if cell is None:
        return "-"
    return f"{cell['mean']:.{digits}f} ± {cell['sd']:.{digits}f}" if cell["sd"] else f"{cell['mean']:.{digits}f}"


def render_report(results: dict[str, Any], ds: SymptomDataset, run_info: dict[str, Any]) -> str:
    test = ds.split_mask("test")
    n_obs = np.array([len(s) for s in ds.sequences])[test]
    syn_rows, sp_rows, strat_rows = [], [], []
    for name, res in results.items():
        s = res["summary"]
        syn = s["syndrome"]
        syn_rows.append({
            "model": name, "seeds": len(res["runs"]), "macro_f1": _fmt(syn["macro_f1"]), "accuracy": _fmt(syn["accuracy"]),
            "critical_error": _fmt(syn["critical_error_rate"]), "nll": _fmt(syn.get("nll")),
            "ece": _fmt(syn.get("ece")), "brier": _fmt(syn.get("brier")),
        })
        if "species" in s:
            sp = s["species"]
            sp_rows.append({"model": name, "accuracy": _fmt(sp["accuracy"]), "macro_f1": _fmt(sp["macro_f1"]),
                            "top3_accuracy": _fmt(sp["top3_accuracy"]), "nll": _fmt(sp["nll"])})
        for group, m in s["stratified"].items():
            strat_rows.append({"model": name, "group": group, "n": int(m["n"]["mean"]), "macro_f1": _fmt(m["macro_f1"]),
                               "accuracy": _fmt(m["accuracy"]), "critical_error": _fmt(m["critical_error_rate"])})
    confusions = []
    for name, res in results.items():
        matrix = pd.DataFrame(res["runs"][0]["metrics"]["confusion"], index=list(SYNDROMES), columns=list(SYNDROMES))
        matrix.index.name = "true \\ predicted"
        confusions += [f"\n### {name} (seed {res['runs'][0]['seed']})\n", matrix.to_markdown()]
    config = run_info["config"]
    parts = [
        f"# Phase 2: symptom-only baselines on `{config['dataset']}`\n",
        HEADER if run_info["SIMULATED"] else "",
        f"- run `{config['name']}`, commit `{run_info['git_commit']}`; dataset `{run_info['dataset']}` "
        f"({run_info['dataset_experiment_type']}, generated at `{run_info['dataset_git_commit']}`)",
        f"- test split: {int(test.sum())} patients, {int((n_obs == 0).sum())} ({(n_obs == 0).mean():.0%}) "
        "with no symptom observed by presentation",
        f"- learned models: train split minus a {config.get('validation_fraction', 0.15):.0%} validation subset "
        f"(early stopping); seeds {config['seeds']}; mean ± sd over seeds. The calibration split is not used.",
        "- inputs: observed symptoms (onset time, time since onset) and presentation time; `xgboost_context` "
        "also sees hour of day / indoor / asleep. GPS and month are placeholders and never used.",
        "\n## Venom syndrome (test split)\n",
        pd.DataFrame(syn_rows).to_markdown(index=False),
        "\nCritical error = share of envenomed patients predicted non-venomous/dry (lower is better). "
        "Models are evaluated at the argmax; no threshold is tuned for the critical error here "
        "(that is the job of the Phase 6 conformal gate).",
        "\n## Species (test split)\n",
        pd.DataFrame(sp_rows).to_markdown(index=False) if sp_rows else "(no species head)",
        "\n## Syndrome by what was observed at presentation (test split)\n",
        pd.DataFrame(strat_rows).to_markdown(index=False),
        "\n## Syndrome confusion matrices (test split)\n",
        *confusions,
    ]
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    out = run(load_config(args.config))
    print(f"wrote results to {out}")


if __name__ == "__main__":
    main()
