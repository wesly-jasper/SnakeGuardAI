"""Metrics for the triage heads, and a CLI that recomputes them from saved predictions.

    python -m src.evaluate --run outputs/phase2/sim_v2

Venom syndrome: accuracy, macro-F1, critical error rate (envenomed predicted as
non-venomous/dry, the most important metric), NLL, ECE and Brier score.
Species: accuracy, macro-F1, top-3 accuracy and NLL.
On simulated data every number is a SIMULATION result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score

from src.data.simulator import DRY_LABEL, SYNDROMES

DRY_INDEX = SYNDROMES.index(DRY_LABEL)
EPS = 1e-12


def critical_error_rate(y_true: np.ndarray, y_pred: np.ndarray, dry_index: int = DRY_INDEX) -> float:
    """Share of truly envenomed patients (label != dry) predicted as non-venomous/dry."""
    envenomed = np.asarray(y_true) != dry_index
    return float((np.asarray(y_pred)[envenomed] == dry_index).mean()) if envenomed.any() else float("nan")


def negative_log_likelihood(proba: np.ndarray, y: np.ndarray) -> float:
    return float(-np.log(np.clip(proba[np.arange(len(y)), y], EPS, 1.0)).mean())


def brier_score(proba: np.ndarray, y: np.ndarray) -> float:
    onehot = np.eye(proba.shape[1])[y]
    return float(((proba - onehot) ** 2).sum(axis=1).mean())


def expected_calibration_error(proba: np.ndarray, y: np.ndarray, n_bins: int = 15) -> float:
    """Top-label ECE with equal-width confidence bins."""
    confidence = proba.max(axis=1)
    correct = proba.argmax(axis=1) == y
    bins = np.minimum((confidence * n_bins).astype(int), n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        in_bin = bins == b
        if in_bin.any():
            ece += in_bin.mean() * abs(correct[in_bin].mean() - confidence[in_bin].mean())
    return float(ece)


def top_k_accuracy(proba: np.ndarray, y: np.ndarray, k: int) -> float:
    top = np.argsort(-proba, axis=1)[:, :k]
    return float((top == y[:, None]).any(axis=1).mean())


def syndrome_metrics(y: np.ndarray, pred: np.ndarray, proba: np.ndarray | None = None) -> dict[str, float]:
    out = {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, labels=list(range(len(SYNDROMES))), average="macro", zero_division=0)),
        "critical_error_rate": critical_error_rate(y, pred),
    }
    if proba is not None:
        out |= {
            "nll": negative_log_likelihood(proba, y),
            "ece": expected_calibration_error(proba, y),
            "brier": brier_score(proba, y),
        }
    return out


def species_metrics(y: np.ndarray, proba: np.ndarray) -> dict[str, float]:
    pred = proba.argmax(axis=1)
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, labels=list(range(proba.shape[1])), average="macro", zero_division=0)),
        "top3_accuracy": top_k_accuracy(proba, y, 3),
        "nll": negative_log_likelihood(proba, y),
    }


def stratified_syndrome(y: np.ndarray, pred: np.ndarray, n_observed: np.ndarray) -> dict[str, dict[str, float]]:
    """Syndrome metrics for patients with no observed symptom at presentation vs. at least one."""
    groups = {"no_observed_symptom": n_observed == 0, "any_observed_symptom": n_observed > 0}
    return {name: syndrome_metrics(y[m], pred[m]) for name, m in groups.items() if m.any()}


def confusion(y: np.ndarray, pred: np.ndarray, n_classes: int) -> np.ndarray:
    matrix = np.zeros((n_classes, n_classes), dtype=int)
    np.add.at(matrix, (y, pred), 1)
    return matrix


def evaluate_predictions(path: Path) -> dict[str, object]:
    """Metrics on the test split from one saved predictions .npz (written by src.train)."""
    data = np.load(path)
    test = data["split"] == "test"
    y_syn, y_sp = data["y_syndrome"][test], data["y_species"][test]
    p_syn = data["p_syndrome"][test] if "p_syndrome" in data else None
    pred = data["pred_syndrome"][test]
    out: dict[str, object] = {"syndrome": syndrome_metrics(y_syn, pred, p_syn)}
    if "p_species" in data:
        out["species"] = species_metrics(y_sp, data["p_species"][test])
    out["stratified"] = stratified_syndrome(y_syn, pred, data["n_observed"][test])
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, help="directory written by src.train")
    args = parser.parse_args(argv)
    results = {p.stem: evaluate_predictions(p) for p in sorted(Path(args.run).glob("predictions_*.npz"))}
    print("SIMULATION RESULTS (synthetic patients)")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
