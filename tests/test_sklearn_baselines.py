"""Tests for the logistic regression and random forest baselines."""

import numpy as np
import pytest

from src.models.registry import resolve_model
from src.models.sklearn_baselines import MISSING_FILL, SklearnHead


def data(n: int = 300) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(n, 4))
    x[rng.random(n) < 0.3, 1] = np.nan  # "not observed" values
    y = np.where(x[:, 0] > 0, 3, 1)      # classes 0 and 2 absent
    return x, y


@pytest.mark.parametrize("kind", ["logistic_regression", "random_forest"])
def test_probability_columns_fixed_and_reproducible(kind: str) -> None:
    x, y = data()
    params = {"n_estimators": 30} if kind == "random_forest" else {}
    head = SklearnHead(kind, 4, params, seed=5).fit(x[:200], y[:200])
    proba = head.predict_proba(x[200:])
    assert proba.shape == (100, 4)
    np.testing.assert_allclose(proba[:, [0, 2]], 0.0)
    np.testing.assert_allclose(proba.sum(1), 1.0)
    assert (proba.argmax(1) == y[200:]).mean() > 0.9
    again = SklearnHead(kind, 4, params, seed=5).fit(x[:200], y[:200]).predict_proba(x[200:])
    np.testing.assert_allclose(proba, again, rtol=0, atol=1e-12)  # parallel averaging order varies in the last bit


def test_preprocessing_fitted_on_training_rows_only() -> None:
    x, y = data()
    head = SklearnHead("logistic_regression", 4).fit(x[:200], y[:200])
    scaler = head.model.named_steps["standardscaler"]
    train = np.where(np.isnan(x[:200]), MISSING_FILL, x[:200])
    np.testing.assert_allclose(scaler.mean_, train.mean(axis=0))
    # Predicting on very different data must not change the fitted statistics.
    head.predict_proba(x[200:] * 100)
    np.testing.assert_allclose(scaler.mean_, train.mean(axis=0))


@pytest.mark.parametrize("kind", ["logistic_regression", "random_forest"])
def test_class_weight_is_configurable(kind: str) -> None:
    x, y = data()
    head = SklearnHead(kind, 4, {"class_weight": "balanced", "n_estimators": 10} if kind == "random_forest"
                       else {"class_weight": "balanced"}).fit(x, y)
    assert head.model.steps[-1][1].class_weight == "balanced"


def test_single_class_and_unknown_kind_rejected() -> None:
    x, _ = data(20)
    with pytest.raises(ValueError):
        SklearnHead("random_forest", 4).fit(x, np.zeros(20, dtype=int))
    with pytest.raises(ValueError):
        SklearnHead("svm", 4).fit(x, np.arange(20) % 2)


def test_registry_resolves_new_baselines_and_rejects_bad_options() -> None:
    assert resolve_model("logistic_regression", {}).kind == "logistic_regression"
    assert resolve_model("random_forest", {"use_context": True}).features.context
    assert resolve_model("xgboost_context", {}).features.context
    assert resolve_model("abl", {"kind": "xgboost", "features": {"onset": False}}).features.onset is False
    with pytest.raises(ValueError):
        resolve_model("svm", {})
    with pytest.raises(ValueError):
        resolve_model("xgboost", {"features": {"made_up": True}})
    with pytest.raises(ValueError):
        resolve_model("transformer", {"features": {"context": True}})
    with pytest.raises(ValueError):
        resolve_model("xgboost", {"heads": ["species"]})
