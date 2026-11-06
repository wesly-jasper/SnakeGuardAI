"""One fit / predict interface for every Phase 2 model.

All models receive `ModelInputs` (src/data/features.py), never the dataset itself, so the
input allowlist applies to every model. Labels are passed separately and only as targets:
the syndrome labels train the syndrome head, the species labels train the species head
(for the transformer, through the species loss on a shared encoder; for tabular models the
heads are independent).

Model kinds: prior, rule, xgboost, logistic_regression, random_forest, transformer.
A config entry is `<name>: {kind?, features?, heads?, params? | transformer options}`;
`kind` defaults to the name (and `xgboost_context` = xgboost with context features).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.data.features import FeatureSpec, ModelInputs, apply_spec, tabular_matrix
from src.data.simulator import DEFAULT_PRECEDENCE, SYNDROMES, derive_syndrome
from src.models.sklearn_baselines import SklearnHead
from src.models.trainer import fit_transformer, predict_proba
from src.models.xgb_baseline import XGBHead

KINDS: tuple[str, ...] = ("prior", "rule", "xgboost", "logistic_regression", "random_forest", "transformer")
TABULAR_KINDS: tuple[str, ...] = ("xgboost", "logistic_regression", "random_forest")
LEARNED_KINDS: tuple[str, ...] = (*TABULAR_KINDS, "transformer")
HEADS: tuple[str, ...] = ("syndrome", "species")
RESERVED_KEYS = {"kind", "features", "heads", "use_context"}
TRANSFORMER_INPUTS = ["sequence: symptom id, onset hours, hours since onset", "presentation_hours"]


@dataclass
class Prediction:
    p_syndrome: np.ndarray | None   # (n, 4) or None for the rule
    pred_syndrome: np.ndarray       # (n,)
    p_species: np.ndarray | None    # (n, n_species) or None


@dataclass
class ModelSpec:
    name: str
    kind: str
    features: FeatureSpec
    heads: tuple[str, ...]
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def learned(self) -> bool:
        return self.kind in LEARNED_KINDS


def resolve_model(name: str, config: dict[str, Any] | None) -> ModelSpec:
    """Model kind, feature spec, heads and hyperparameters from one config entry."""
    config = dict(config or {})
    kind = config.get("kind", "xgboost" if name == "xgboost_context" else name)
    if kind not in KINDS:
        raise ValueError(f"unknown model kind {kind!r} for {name!r}; expected one of {KINDS}")
    features = dict(config.get("features") or {})
    if name == "xgboost_context" or config.get("use_context"):
        features.setdefault("context", True)
    spec = FeatureSpec.from_dict(features)
    heads = tuple(config.get("heads", HEADS))
    if "syndrome" not in heads or set(heads) - set(HEADS):
        raise ValueError(f"heads must include 'syndrome' and be a subset of {HEADS}")
    if kind == "transformer":
        params = {k: v for k, v in config.items() if k not in RESERVED_KEYS}
        allowed = FeatureSpec(drop_symptoms=spec.drop_symptoms, drop_groups=spec.drop_groups)
        if spec != allowed:
            raise ValueError("the transformer supports only drop_symptoms / drop_groups feature options")
    else:
        params = dict(config.get("params") or {})
    return ModelSpec(name, kind, spec, heads, params)


class FittedModel:
    spec: ModelSpec
    feature_names: list[str]
    supports_missing_presentation: bool = False

    def predict(self, inputs: ModelInputs) -> Prediction:
        raise NotImplementedError

    def _check_presentation(self, inputs: ModelInputs) -> None:
        if not self.supports_missing_presentation and np.isnan(inputs.presentation).any():
            raise ValueError(f"{self.spec.name} does not support missing presentation time")


class PriorModel(FittedModel):
    """Training-set class frequencies for every patient."""

    supports_missing_presentation = True

    def __init__(self, spec: ModelSpec, y_syn: np.ndarray, y_sp: np.ndarray, n_species: int) -> None:
        self.spec, self.feature_names = spec, []
        self.syndrome = np.bincount(y_syn, minlength=len(SYNDROMES)) / len(y_syn)
        self.species = np.bincount(y_sp, minlength=n_species) / len(y_sp)

    def predict(self, inputs: ModelInputs) -> Prediction:
        n = len(inputs)
        p_syn = np.tile(self.syndrome, (n, 1))
        return Prediction(p_syn, p_syn.argmax(1), np.tile(self.species, (n, 1)))


class RuleModel(FittedModel):
    """Phase 1 syndromic rule on observed symptoms; any observed symptom counts as envenoming."""

    supports_missing_presentation = True

    def __init__(self, spec: ModelSpec, precedence: tuple[str, ...]) -> None:
        self.spec, self.precedence = spec, precedence
        self.feature_names = ["observed symptom set (knowledge-table markers)"]

    def predict(self, inputs: ModelInputs) -> Prediction:
        inputs = apply_spec(inputs, self.spec.features)
        labels = [
            derive_syndrome((inputs.symptoms[int(i)] for i in seq[:, 0]), inputs.markers, True, self.precedence)
            for seq in inputs.sequences
        ]
        return Prediction(None, np.array([SYNDROMES.index(label) for label in labels]), None)


class TabularModel(FittedModel):
    def __init__(self, spec: ModelSpec, heads: dict[str, Any], feature_names: list[str], info: dict[str, Any]) -> None:
        self.spec, self.heads, self.feature_names, self.info = spec, heads, feature_names, info
        self.supports_missing_presentation = spec.kind == "xgboost"  # native NaN handling

    def predict(self, inputs: ModelInputs) -> Prediction:
        self._check_presentation(inputs)
        x, names = tabular_matrix(inputs, self.spec.features)
        if names != self.feature_names:
            raise ValueError("feature columns differ from training")
        p_syn = self.heads["syndrome"].predict_proba(x)
        p_sp = self.heads["species"].predict_proba(x) if "species" in self.heads else None
        return Prediction(p_syn, p_syn.argmax(1), p_sp)


class TransformerModel(FittedModel):
    def __init__(self, spec: ModelSpec, model: Any, info: dict[str, Any]) -> None:
        self.spec, self.model, self.info = spec, model, info
        self.feature_names = list(TRANSFORMER_INPUTS)

    def predict(self, inputs: ModelInputs) -> Prediction:
        self._check_presentation(inputs)
        inputs = apply_spec(inputs, self.spec.features)
        p_syn, p_sp = predict_proba(self.model, list(inputs.sequences), inputs.presentation, np.arange(len(inputs)))
        return Prediction(p_syn, p_syn.argmax(1), p_sp)


def fit_model(
    spec: ModelSpec, inputs: ModelInputs, y_syndrome: np.ndarray, y_species: np.ndarray, fit_idx: np.ndarray,
    val_idx: np.ndarray, seed: int, n_species: int, precedence: tuple[str, ...] = DEFAULT_PRECEDENCE,
) -> FittedModel:
    """Fit one model on `fit_idx` (early stopping on `val_idx` where used)."""
    if spec.kind == "prior":
        return PriorModel(spec, y_syndrome[fit_idx], y_species[fit_idx], n_species)
    if spec.kind == "rule":
        return RuleModel(spec, precedence)
    targets = {"syndrome": (y_syndrome, len(SYNDROMES)), "species": (y_species, n_species)}
    if spec.kind in TABULAR_KINDS:
        x, names = tabular_matrix(inputs, spec.features)
        heads: dict[str, Any] = {}
        info: dict[str, Any] = {}
        for head in spec.heads:
            y, k = targets[head]
            if spec.kind == "xgboost":
                heads[head] = XGBHead(k, spec.params, seed).fit(x[fit_idx], y[fit_idx], x[val_idx], y[val_idx])
                info[f"{head}_best_iteration"] = int(heads[head].model.best_iteration)
            else:
                heads[head] = SklearnHead(spec.kind, k, spec.params, seed).fit(x[fit_idx], y[fit_idx])
        return TabularModel(spec, heads, names, info)
    if spec.kind == "transformer":
        if spec.heads != HEADS:
            raise ValueError("the transformer always trains both heads")
        used = apply_spec(inputs, spec.features)
        result = fit_transformer(
            list(used.sequences), used.presentation, y_syndrome, y_species, fit_idx, val_idx,
            len(inputs.symptoms), len(SYNDROMES), n_species, spec.params, seed,
        )
        info = {"best_epoch": result.best_epoch, "epochs_run": len(result.history),
                "final_val_loss": min(h["val_loss"] for h in result.history)}
        return TransformerModel(spec, result.model, info)
    raise ValueError(spec.kind)
