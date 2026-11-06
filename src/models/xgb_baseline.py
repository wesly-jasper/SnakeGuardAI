"""Symptom-only XGBoost baseline (Phase 2): one classifier per output head."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from xgboost import XGBClassifier

DEFAULT_PARAMS: dict[str, Any] = {
    "n_estimators": 600,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "early_stopping_rounds": 30,
}


@dataclass
class XGBHead:
    """Multiclass XGBoost for one head; `n_classes` fixes the probability columns even if a
    class is absent from the training data."""

    n_classes: int
    params: dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    model: XGBClassifier | None = None
    classes_: np.ndarray | None = None

    def fit(self, x: np.ndarray, y: np.ndarray, x_val: np.ndarray, y_val: np.ndarray) -> "XGBHead":
        # XGBoost needs labels 0..m-1, so remap the classes that occur in training.
        self.classes_ = np.unique(y)
        if len(self.classes_) < 2:
            raise ValueError("need at least two classes in the training data")
        remap = {c: i for i, c in enumerate(self.classes_)}
        keep = np.isin(y_val, self.classes_)
        self.model = XGBClassifier(
            **{**DEFAULT_PARAMS, **self.params},
            eval_metric="mlogloss" if len(self.classes_) > 2 else "logloss",
            random_state=self.seed,
            n_jobs=-1,
        )
        self.model.fit(
            x, np.vectorize(remap.get)(y),
            eval_set=[(x_val[keep], np.vectorize(remap.get)(y_val[keep]))],
            verbose=False,
        )
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self.model is None or self.classes_ is None:
            raise RuntimeError("fit the model first")
        proba = np.zeros((len(x), self.n_classes))
        proba[:, self.classes_] = self.model.predict_proba(x)
        return proba
