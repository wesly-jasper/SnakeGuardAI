"""Threshold evaluation of P(envenomed) as an experimental decision policy. RESEARCH ONLY.

For a threshold t, a patient with P(envenomed) >= t is "referred for further assessment" and
one with P(envenomed) < t is "low risk". P(envenomed) = 1 - P(non-venomous/dry) from the
syndrome head. The table shows the trade-off between referral rate and envenomed patients
classified low risk, so that the calibrated probabilities can be judged beyond the argmax.

This is NOT a clinical decision rule. No threshold here is validated, approved or safe; any
clinical threshold needs independent validation on real patients and clinician approval.
A model score must never be used to withhold medical assessment. On simulated data every
number is a SIMULATION result. Thresholds are listed, not selected: nothing is tuned on the
test split (selecting a threshold, if ever, belongs on the calibration split, Phase 6).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from src.evaluate import DRY_INDEX

DEFAULT_THRESHOLDS: tuple[float, ...] = (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5)
DISCLAIMER = (
    "Research evaluation only: thresholds are illustrative, not clinically validated or approved, "
    "and must never be used to withhold medical assessment."
)
PROBABILITY_TOLERANCE = 1e-6
# P(envenomed) is computed as 1 - P(dry), so a value meant to equal the threshold can land a
# rounding error below it; ties (within this tolerance) are referred, the conservative side.
TIE_TOLERANCE = 1e-9


def validate_probabilities(proba: np.ndarray, n_classes: int | None = None) -> np.ndarray:
    """Check a (n, k) probability matrix: finite, within [0, 1], rows summing to 1."""
    proba = np.asarray(proba, dtype=float)
    if proba.ndim != 2 or (n_classes is not None and proba.shape[1] != n_classes):
        raise ValueError(f"expected a (n, {n_classes or 'k'}) probability matrix, got shape {proba.shape}")
    if not np.isfinite(proba).all():
        raise ValueError("probabilities must be finite")
    if (proba < -PROBABILITY_TOLERANCE).any() or (proba > 1 + PROBABILITY_TOLERANCE).any():
        raise ValueError("probabilities must lie in [0, 1]")
    if len(proba) and not np.allclose(proba.sum(axis=1), 1.0, atol=1e-4):
        raise ValueError("probability rows must sum to 1")
    return proba


def validate_thresholds(thresholds: Sequence[float]) -> list[float]:
    values = [float(t) for t in thresholds]
    if not values or any(not (0.0 <= t <= 1.0) or not np.isfinite(t) for t in values):
        raise ValueError("thresholds must be a non-empty list of numbers in [0, 1]")
    return sorted(set(values))


def p_envenomed(p_syndrome: np.ndarray, dry_index: int = DRY_INDEX) -> np.ndarray:
    """P(envenomed) = 1 - P(non-venomous/dry), clipped to [0, 1]."""
    proba = validate_probabilities(p_syndrome)
    return np.clip(1.0 - proba[:, dry_index], 0.0, 1.0)


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def threshold_row(envenomed: np.ndarray, p_env: np.ndarray, threshold: float) -> dict[str, float]:
    """Metrics of the policy 'refer if P(envenomed) >= threshold' (a tie is referred)."""
    refer = p_env >= threshold - TIE_TOLERANCE
    low = ~refer
    tp = int((refer & envenomed).sum())
    fn = int((low & envenomed).sum())   # envenomed classified low risk
    tn = int((low & ~envenomed).sum())
    fp = int((refer & ~envenomed).sum())
    n = len(envenomed)
    return {
        "threshold": float(threshold),
        "n": n,
        "n_low_risk": int(low.sum()),
        "n_referred": int(refer.sum()),
        "n_envenomed": int(envenomed.sum()),
        "n_envenomed_low_risk": fn,
        "sensitivity": _ratio(tp, tp + fn),
        "specificity": _ratio(tn, tn + fp),
        "npv": _ratio(tn, tn + fn),
        "ppv": _ratio(tp, tp + fp),
        "referral_rate": _ratio(int(refer.sum()), n),
        "critical_error_rate": _ratio(fn, tp + fn),
    }


def threshold_table(
    y_syndrome: np.ndarray, p_syndrome: np.ndarray, thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    dry_index: int = DRY_INDEX,
) -> list[dict[str, float]]:
    """One row per threshold; empty input or a missing class gives NaN ratios, not errors."""
    y = np.asarray(y_syndrome)
    if len(y) != len(p_syndrome):
        raise ValueError("labels and probabilities differ in length")
    p_env = p_envenomed(p_syndrome, dry_index)
    envenomed = y != dry_index
    return [threshold_row(envenomed, p_env, t) for t in validate_thresholds(thresholds)]


def policy_evaluation(
    y_syndrome: np.ndarray, p_syndrome: np.ndarray, n_observed: np.ndarray,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
) -> dict[str, list[dict[str, float]]]:
    """Threshold tables for all patients and for those with no symptom observed at presentation."""
    none = np.asarray(n_observed) == 0
    p = np.asarray(p_syndrome)
    return {
        "all": threshold_table(y_syndrome, p, thresholds),
        "no_observed_symptom": threshold_table(np.asarray(y_syndrome)[none], p[none], thresholds),
    }
