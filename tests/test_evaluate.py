"""Tests for the metrics in src/evaluate.py."""

import numpy as np
import pytest

from src.evaluate import (
    DRY_INDEX,
    brier_score,
    confusion,
    critical_error_rate,
    expected_calibration_error,
    negative_log_likelihood,
    stratified_syndrome,
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
