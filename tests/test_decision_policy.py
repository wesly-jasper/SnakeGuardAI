"""Tests for the research-only threshold policy in src/decision_policy.py."""

import numpy as np
import pytest

from src.decision_policy import (
    p_envenomed,
    policy_evaluation,
    threshold_row,
    threshold_table,
    validate_probabilities,
    validate_thresholds,
)

# columns: neurotoxic, haemotoxic, local-only, non-venomous/dry
PROBA = np.array([
    [0.6, 0.1, 0.1, 0.2],    # P(env) 0.8, envenomed
    [0.05, 0.05, 0.0, 0.9],  # P(env) 0.1, envenomed  -> missed at t > 0.1
    [0.0, 0.0, 0.3, 0.7],    # P(env) 0.3, dry
    [0.0, 0.0, 0.0, 1.0],    # P(env) 0.0, dry
])
Y = np.array([0, 1, 3, 3])


def test_p_envenomed() -> None:
    np.testing.assert_allclose(p_envenomed(PROBA), [0.8, 0.1, 0.3, 0.0])


def test_threshold_row_counts_and_ratios() -> None:
    row = threshold_row(Y != 3, p_envenomed(PROBA), 0.2)
    assert row["n_referred"] == 2 and row["n_low_risk"] == 2
    assert row["n_envenomed_low_risk"] == 1
    assert row["sensitivity"] == 0.5 and row["specificity"] == 0.5
    assert row["npv"] == 0.5 and row["ppv"] == 0.5
    assert row["referral_rate"] == 0.5 and row["critical_error_rate"] == 0.5


def test_threshold_boundary_is_referred() -> None:
    row = threshold_row(Y != 3, p_envenomed(PROBA), 0.1)  # P(env) == 0.1 exactly
    assert row["n_envenomed_low_risk"] == 0 and row["sensitivity"] == 1.0
    zero = threshold_row(Y != 3, p_envenomed(PROBA), 0.0)
    assert zero["n_referred"] == 4 and np.isnan(zero["npv"])  # nobody low risk
    one = threshold_row(Y != 3, p_envenomed(PROBA), 1.0)
    assert one["n_referred"] == 0 and np.isnan(one["ppv"]) and one["critical_error_rate"] == 1.0


def test_sensitivity_is_monotone_in_threshold() -> None:
    rng = np.random.default_rng(0)
    proba = rng.dirichlet(np.ones(4), size=300)
    y = rng.integers(0, 4, 300)
    rows = threshold_table(y, proba, [0.9, 0.05, 0.5, 0.2])
    assert [r["threshold"] for r in rows] == [0.05, 0.2, 0.5, 0.9]  # sorted
    sens = [r["sensitivity"] for r in rows]
    refer = [r["referral_rate"] for r in rows]
    assert sens == sorted(sens, reverse=True) and refer == sorted(refer, reverse=True)


def test_missing_class_and_empty_input_give_nan() -> None:
    only_dry = threshold_table(np.array([3, 3]), PROBA[2:], [0.5])[0]
    assert np.isnan(only_dry["sensitivity"]) and only_dry["n_envenomed"] == 0
    empty = threshold_table(np.array([], dtype=int), np.zeros((0, 4)), [0.5])[0]
    assert empty["n"] == 0 and np.isnan(empty["referral_rate"])


def test_policy_evaluation_groups() -> None:
    out = policy_evaluation(Y, PROBA, np.array([1, 0, 0, 2]), [0.2])
    assert out["all"][0]["n"] == 4
    assert out["no_observed_symptom"][0]["n"] == 2
    assert out["no_observed_symptom"][0]["n_envenomed_low_risk"] == 1


@pytest.mark.parametrize("bad", [
    np.array([[0.5, 0.5, 0.1, 0.0]]),        # rows do not sum to 1
    np.array([[1.2, -0.2, 0.0, 0.0]]),       # outside [0, 1]
    np.array([[np.nan, 0.5, 0.5, 0.0]]),     # not finite
    np.array([0.2, 0.8]),                    # not 2-D
])
def test_invalid_probabilities_rejected(bad: np.ndarray) -> None:
    with pytest.raises(ValueError):
        validate_probabilities(bad)


def test_wrong_width_and_length_rejected() -> None:
    with pytest.raises(ValueError):
        validate_probabilities(PROBA[:, :3], n_classes=4)
    with pytest.raises(ValueError):
        threshold_table(Y[:3], PROBA, [0.5])


@pytest.mark.parametrize("bad", [[], [1.5], [-0.1], [float("nan")]])
def test_invalid_thresholds_rejected(bad: list) -> None:
    with pytest.raises(ValueError):
        validate_thresholds(bad)
