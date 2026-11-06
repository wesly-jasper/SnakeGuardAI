"""Tests for the metrics in src/evaluate.py."""

import numpy as np
import pytest

from src.evaluate import (
    DRY_INDEX,
    brier_score,
    confusion,
    critical_error_detail,
    critical_error_rate,
    envenomation_metrics,
    expected_calibration_error,
    negative_log_likelihood,
    per_class_metrics,
    stratified_syndrome,
    syndrome_metrics,
    top_k_accuracy,
)


def test_dry_index_is_non_venomous_label() -> None:
    assert DRY_INDEX == 3


def test_critical_error_counts_only_envenomed_predicted_dry() -> None:
    y = np.array([0, 1, 2, 3, 3])
    pred = np.array([3, 1, 3, 0, 3])
    assert critical_error_rate(y, pred) == pytest.approx(2 / 3)
    assert np.isnan(critical_error_rate(np.array([3]), np.array([0])))


def test_probability_metrics() -> None:
    proba = np.array([[1.0, 0.0], [0.5, 0.5]])
    y = np.array([0, 1])
    assert negative_log_likelihood(proba, y) == pytest.approx(np.log(2) / 2)
    assert brier_score(proba, y) == pytest.approx(0.25)
    assert top_k_accuracy(np.array([[0.1, 0.5, 0.4]]), np.array([2]), 1) == 0.0
    assert top_k_accuracy(np.array([[0.1, 0.5, 0.4]]), np.array([2]), 2) == 1.0


def test_ece_zero_when_calibrated_and_positive_when_overconfident() -> None:
    proba = np.tile([0.75, 0.25], (4, 1))
    assert expected_calibration_error(proba, np.array([0, 0, 0, 1])) == pytest.approx(0.0)
    assert expected_calibration_error(np.tile([1.0, 0.0], (2, 1)), np.array([0, 1])) == pytest.approx(0.5)


def test_confusion_and_stratification() -> None:
    y, pred = np.array([0, 0, 3]), np.array([0, 3, 3])
    np.testing.assert_array_equal(confusion(y, pred, 4)[0], [1, 0, 0, 1])
    strata = stratified_syndrome(y, pred, np.array([2, 0, 0]))
    assert strata["no_observed_symptom"]["critical_error_rate"] == 1.0
    assert strata["any_observed_symptom"]["n"] == 1


def test_per_class_metrics_values_and_missing_class() -> None:
    y = np.array([0, 0, 1, 3])
    pred = np.array([0, 1, 1, 3])  # class 2 (local-only) never occurs
    m = per_class_metrics(y, pred)
    assert m["neurotoxic"]["precision"] == 1.0 and m["neurotoxic"]["recall"] == 0.5
    assert m["haemotoxic"]["precision"] == 0.5 and m["haemotoxic"]["recall"] == 1.0
    assert m["haemotoxic"]["specificity"] == pytest.approx(2 / 3)
    assert m["local-only"] == {"precision": 0.0, "recall": 0.0, "f1": 0.0, "sensitivity": 0.0,
                               "specificity": 1.0, "support": 0}
    assert m["neurotoxic"]["sensitivity"] == m["neurotoxic"]["recall"]


def test_per_class_metrics_empty_input_is_nan_not_error() -> None:
    m = per_class_metrics(np.array([], dtype=int), np.array([], dtype=int))
    assert np.isnan(m["neurotoxic"]["recall"]) and np.isnan(m["neurotoxic"]["specificity"])
    assert m["neurotoxic"]["support"] == 0


def test_envenomation_metrics() -> None:
    m = envenomation_metrics(np.array([0, 1, 3, 3]), np.array([3, 1, 3, 0]))
    assert m["envenomation_sensitivity"] == 0.5 and m["envenomation_specificity"] == 0.5
    only_dry = envenomation_metrics(np.array([3]), np.array([3]))
    assert np.isnan(only_dry["envenomation_sensitivity"]) and only_dry["envenomation_specificity"] == 1.0


def test_critical_error_detail_counts_and_groups() -> None:
    y = np.array([0, 0, 1, 2, 3])
    pred = np.array([3, 0, 3, 2, 3])
    d = critical_error_detail(y, pred, n_observed=np.array([0, 1, 0, 1, 0]))
    assert (d["numerator"], d["denominator"]) == (2, 4) and d["rate"] == 0.5
    assert d["n_envenomed"] == 4 and d["n_envenomed_predicted_dry"] == 2
    assert d["by_syndrome"]["neurotoxic"] == {"numerator": 1, "denominator": 2, "rate": 0.5}
    assert d["by_syndrome"]["local-only"]["rate"] == 0.0
    assert "non-venomous/dry" not in d["by_syndrome"]
    assert d["no_observed_symptom"] == {"numerator": 2, "denominator": 2, "rate": 1.0}
    assert d["any_observed_symptom"]["rate"] == 0.0
    # rate matches the existing definition
    assert d["rate"] == critical_error_rate(y, pred)


def test_critical_error_detail_empty_group_is_nan() -> None:
    d = critical_error_detail(np.array([3, 3]), np.array([3, 3]), n_observed=np.array([1, 1]))
    assert d["denominator"] == 0 and np.isnan(d["rate"])
    assert np.isnan(d["no_observed_symptom"]["rate"])


def test_syndrome_metrics_keeps_existing_keys_and_adds_new() -> None:
    y, pred = np.array([0, 1, 2, 3]), np.array([0, 1, 3, 3])
    proba = np.eye(4)[pred] * 0.9 + 0.025
    m = syndrome_metrics(y, pred, proba)
    for key in ("n", "accuracy", "macro_f1", "critical_error_rate", "nll", "ece", "brier"):
        assert key in m
    assert m["critical_error_rate"] == critical_error_rate(y, pred)
    assert 0 <= m["weighted_f1"] <= 1 and "recall_local-only" in m and "specificity_neurotoxic" in m
    empty = syndrome_metrics(np.array([], dtype=int), np.array([], dtype=int))
    assert empty["n"] == 0 and np.isnan(empty["macro_f1"])
