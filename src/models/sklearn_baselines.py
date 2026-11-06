"""Conventional ML baselines (Phase 2 hardening): logistic regression and random forest.

Each head is an sklearn Pipeline fitted on training rows only, so imputation and scaling
statistics never see calibration or test data. Missing values in the tabular features mean
"symptom not observed" (onset / time since onset); they are imputed with a constant (no
statistics are learned from the data) and the `present_<s>` columns keep the information.
Hyperparameters are fixed in the config; nothing is tuned on calibration or test data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

LOGISTIC_DEFAULTS: dict[str, Any] = {"C": 1.0, "max_iter": 2000, "class_weight": None}
FOREST_DEFAULTS: dict[str, Any] = {
    "n_estimators": 300, "max_depth": None, "min_samples_leaf": 5, "class_weight": None, "n_jobs": -1,
}
# Constant used for "not observed" onset / elapsed times. -1 h is outside the valid range
# (hours are >= 0), so trees can separate it; for logistic regression it is standardised
# together with the observed values and the presence flags carry the main signal.
MISSING_FILL = -1.0


def logistic_pipeline(params: dict[str, Any], seed: int) -> Pipeline:
    cfg = {**LOGISTIC_DEFAULTS, **params}
    return make_pipeline(
        SimpleImputer(strategy="constant", fill_value=MISSING_FILL, keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(C=cfg["C"], max_iter=cfg["max_iter"], class_weight=cfg["class_weight"], random_state=seed),
    )


def forest_pipeline(params: dict[str, Any], seed: int) -> Pipeline:
    cfg = {**FOREST_DEFAULTS, **params}
    return make_pipeline(
        SimpleImputer(strategy="constant", fill_value=MISSING_FILL, keep_empty_features=True),
        RandomForestClassifier(
            n_estimators=cfg["n_estimators"], max_depth=cfg["max_depth"], min_samples_leaf=cfg["min_samples_leaf"],
            class_weight=cfg["class_weight"], n_jobs=cfg["n_jobs"], random_state=seed,
        ),
    )


BUILDERS = {"logistic_regression": logistic_pipeline, "random_forest": forest_pipeline}


@dataclass
class SklearnHead:
    """One output head; probability columns are fixed to `n_classes` even if a class is
    absent from the training data."""

    kind: str
    n_classes: int
    params: dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    model: Pipeline | None = None

    def fit(self, x: np.ndarray, y: np.ndarray) -> "SklearnHead":
        if self.kind not in BUILDERS:
            raise ValueError(f"unknown sklearn baseline {self.kind!r}")
        if len(np.unique(y)) < 2:
            raise ValueError("need at least two classes in the training data")
        self.model = BUILDERS[self.kind](self.params, self.seed).fit(x, y)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("fit the model first")
        proba = np.zeros((len(x), self.n_classes))
        proba[:, self.model.classes_.astype(int)] = self.model.predict_proba(x)
        return proba
