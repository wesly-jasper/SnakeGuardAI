"""Metrics for the triage heads, and a CLI that recomputes them from saved predictions.

    python -m src.evaluate --run outputs/phase2/sim_v2

Venom syndrome: accuracy, macro-F1, weighted F1, per-class precision / recall (sensitivity) /
F1 / specificity (one-vs-rest), envenomation sensitivity / specificity, critical error rate
(envenomed predicted as non-venomous/dry, the most important metric) with its numerator,
denominator and breakdown by true syndrome and by what was observed, NLL, ECE and Brier score.
Species: accuracy, macro-F1, top-3 accuracy and NLL.
Empty groups and classes absent from a split give NaN, never an exception.
On simulated data every number is a SIMULATION result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

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


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def per_class_metrics(y: np.ndarray, pred: np.ndarray, labels: tuple[str, ...] = SYNDROMES) -> dict[str, dict[str, float]]:
    """One-vs-rest precision, recall (= sensitivity), F1, specificity and support per class.
    A class with no true or no predicted members gets 0 for precision/recall/F1 (sklearn's
    zero_division=0) and NaN specificity if there are no negatives."""
    y, pred = np.asarray(y), np.asarray(pred)
    k = len(labels)
    precision, recall, f1, support = precision_recall_fscore_support(
        y, pred, labels=list(range(k)), zero_division=0,
    ) if len(y) else (np.full(k, np.nan),) * 3 + (np.zeros(k, dtype=int),)
    out = {}
    for c, label in enumerate(labels):
        negatives = y != c
        out[label] = {
            "precision": float(precision[c]), "recall": float(recall[c]), "f1": float(f1[c]),
            "sensitivity": float(recall[c]),
            "specificity": _ratio(int((pred[negatives] != c).sum()), int(negatives.sum())),
            "support": int(support[c]),
        }
    return out


def envenomation_metrics(y: np.ndarray, pred: np.ndarray, dry_index: int = DRY_INDEX) -> dict[str, float]:
    """Binary view envenomed (label != dry) vs not, at the predicted syndrome."""
    y, pred = np.asarray(y), np.asarray(pred)
    env, pred_env = y != dry_index, pred != dry_index
    return {
        "envenomation_sensitivity": _ratio(int((env & pred_env).sum()), int(env.sum())),
        "envenomation_specificity": _ratio(int((~env & ~pred_env).sum()), int((~env).sum())),
    }


def critical_error_detail(y: np.ndarray, pred: np.ndarray, n_observed: np.ndarray | None = None,
                          dry_index: int = DRY_INDEX) -> dict[str, object]:
    """Critical error with numerator / denominator, by true syndrome and by observed-symptom group.
    Definition unchanged: truly envenomed patients predicted non-venomous/dry."""
    y, pred = np.asarray(y), np.asarray(pred)

    def count(mask: np.ndarray) -> dict[str, float]:
        env = mask & (y != dry_index)
        missed = int((pred[env] == dry_index).sum())
        return {"numerator": missed, "denominator": int(env.sum()), "rate": _ratio(missed, int(env.sum()))}

    everyone = np.ones(len(y), dtype=bool)
    out: dict[str, object] = {
        **count(everyone),
        "n_envenomed": int((y != dry_index).sum()),
        "n_envenomed_predicted_dry": count(everyone)["numerator"],
        "by_syndrome": {label: count(y == c) for c, label in enumerate(SYNDROMES) if c != dry_index},
    }
    if n_observed is not None:
        n_observed = np.asarray(n_observed)
        out["no_observed_symptom"] = count(n_observed == 0)
        out["any_observed_symptom"] = count(n_observed > 0)
    return out


def syndrome_metrics(y: np.ndarray, pred: np.ndarray, proba: np.ndarray | None = None) -> dict[str, float]:
    """Scalar syndrome metrics; existing keys keep their definitions, new keys are added."""
    labels = list(range(len(SYNDROMES)))
    if len(y) == 0:
        nan = float("nan")
        out = {"n": 0, "accuracy": nan, "macro_f1": nan, "critical_error_rate": nan, "weighted_f1": nan}
        return out | ({"nll": nan, "ece": nan, "brier": nan} if proba is not None else {})
    out = {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, labels=labels, average="macro", zero_division=0)),
        "critical_error_rate": critical_error_rate(y, pred),
        "weighted_f1": float(f1_score(y, pred, labels=labels, average="weighted", zero_division=0)),
        **envenomation_metrics(y, pred),
    }
    for label, values in per_class_metrics(y, pred).items():
        out |= {f"{metric}_{label}": values[metric] for metric in ("precision", "recall", "f1", "specificity")}
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
