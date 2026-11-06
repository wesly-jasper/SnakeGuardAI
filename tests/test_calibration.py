"""Tests for post-hoc calibration (src/uncertainty/calibration.py)."""

import numpy as np
import pytest

from src.uncertainty.calibration import (
    binary_metrics,
    evaluate_calibration,
    fit_binary,
    fit_multiclass,
    isotonic_supported,
    reliability_table,
)


def overconfident(n: int = 4000, k: int = 4, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Labels drawn from true probabilities; predictions are those probabilities sharpened (T=0.4)."""
    rng = np.random.default_rng(seed)
    logits = rng.normal(0, 1.0, (n, k))
    true = np.exp(logits) / np.exp(logits).sum(1, keepdims=True)
    y = np.array([rng.choice(k, p=row) for row in true])
    sharp = np.exp(logits / 0.4)
    return sharp / sharp.sum(1, keepdims=True), y


@pytest.mark.parametrize("method", ["temperature", "sigmoid", "isotonic"])
def test_multiclass_outputs_are_distributions_and_improve_nll(method: str) -> None:
    p, y = overconfident()
    cal = fit_multiclass(method, p[:2000], y[:2000])
    q = cal.apply(p[2000:])
    assert q.shape == p[2000:].shape and np.allclose(q.sum(1), 1) and (q >= 0).all()
    from src.evaluate import negative_log_likelihood as nll
    assert nll(q, y[2000:]) < nll(p[2000:], y[2000:])


def test_temperature_recovers_sharpening() -> None:
    p, y = overconfident(n=20000)
    t = fit_multiclass("temperature", p, y).params["temperature"]
    assert 2.0 < t < 3.0  # predictions were sharpened by 1/0.4 = 2.5


@pytest.mark.parametrize("method", ["temperature", "sigmoid", "isotonic"])
def test_binary_calibrators(method: str) -> None:
    rng = np.random.default_rng(1)
    true = rng.uniform(0.05, 0.95, 5000)
    y = (rng.random(5000) < true).astype(int)
    p = 1 / (1 + np.exp(-2.5 * np.log(true / (1 - true))))  # overconfident
    cal = fit_binary(method, p[:2500], y[:2500])
    q = cal.apply(p[2500:])
    assert ((q >= 0) & (q <= 1)).all()
    assert binary_metrics(q, y[2500:])["nll"] < binary_metrics(p[2500:], y[2500:])["nll"]


def test_unknown_method() -> None:
    p, y = overconfident(n=100)
    with pytest.raises(ValueError):
        fit_multiclass("beta", p, y)
    with pytest.raises(ValueError):
        fit_binary("beta", p[:, 0], (y == 0).astype(int))


def test_isotonic_sample_size_rule() -> None:
    assert not isotonic_supported(np.zeros(500, int), 4)[0]
    y = np.repeat(np.arange(4), 300)
    assert isotonic_supported(y, 4)[0]
    assert not isotonic_supported(np.r_[y, np.full(10, 3)][:-1200 + 10], 4)[0]


def test_evaluate_calibration_never_uses_eval_labels() -> None:
    p, y = overconfident()
    fit = np.zeros(len(y), bool)
    fit[:2000] = True
    report_a, arrays_a = evaluate_calibration(p, y, fit, ~fit)
    y_scrambled = y.copy()
    y_scrambled[~fit] = np.random.default_rng(9).permutation(y[~fit])
    report_b, arrays_b = evaluate_calibration(p, y_scrambled, fit, ~fit)
    assert report_a["methods"] == report_b["methods"]  # fitted parameters unchanged
    for key in arrays_a:
        np.testing.assert_array_equal(arrays_a[key], arrays_b[key])
    # raw probabilities kept and every method reported with and without help flags
    np.testing.assert_allclose(arrays_a["p_envenomed_raw"], 1 - p[:, 3])
    for method in ("temperature", "sigmoid", "isotonic"):
        assert "helps_nll" in report_a["syndrome"][method]
        assert "helps_nll" in report_a["envenomed"][method]


def test_evaluate_calibration_rejects_overlap_and_skips_small_isotonic() -> None:
    p, y = overconfident(n=600)
    fit = np.zeros(600, bool)
    fit[:300] = True
    with pytest.raises(ValueError):
        evaluate_calibration(p, y, np.ones(600, bool), ~fit)
    report, arrays = evaluate_calibration(p, y, fit, ~fit)
    assert "isotonic" in report["skipped"] and "p_syndrome_isotonic" not in arrays


def test_reliability_and_metrics_known_values() -> None:
    p = np.array([0.05, 0.05, 0.95, 0.95])
    y = np.array([0, 0, 1, 1])
    rows = reliability_table(p, y)
    assert [r["n"] for r in rows] == [2, 2]
    assert rows[0]["observed"] == 0 and rows[1]["observed"] == 1
    m = binary_metrics(p, y)
    assert m["brier"] == pytest.approx(0.0025) and m["ece"] == pytest.approx(0.05)
    assert np.isnan(binary_metrics(np.array([]), np.array([]))["nll"])
