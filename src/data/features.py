"""Strict model-input allowlist and feature construction (Phase 2 hardening).

Every model gets its inputs through `build_inputs`, the only function that reads patient
columns, and only through `select_allowed`, which refuses anything not on the allowlist.
What a model may see (what is known when the patient presents):
- observed symptom events (symptom, onset hours), already filtered in `src/data/dataset.py`
  to events with a known onset at or before presentation;
- `presentation_hours` (time from bite to presentation);
- context columns `hour_of_day`, `indoor`, `asleep`, only when a model asks for them.

Never allowed: targets (`species`, `venom_syndrome`, `dry_bite`), split and ids, simulator
diagnostics (`order_violations`, `n_assumed_onsets`, `n_unknown_onsets`), the per-patient
`onset_*` columns of patients.csv (inputs come from events.csv instead), and the GPS / month
placeholders (uniform noise until the Phase 3 geo prior).

`FeatureSpec` switches input blocks on and off for ablations; `tabular_matrix` builds the
fixed-width matrix for tabular models and validates every column name against the allowlist.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, fields, replace
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.data.dataset import SymptomDataset

ALLOWED_INPUT_COLUMNS: frozenset[str] = frozenset({"presentation_hours"})
ALLOWED_CONTEXT_COLUMNS: frozenset[str] = frozenset({"hour_of_day", "indoor", "asleep"})
DEFAULT_CONTEXT_COLUMNS: tuple[str, ...] = ("hour_of_day", "indoor", "asleep")
FORBIDDEN_COLUMNS: frozenset[str] = frozenset({
    "patient_id", "split",                                            # bookkeeping
    "species", "venom_syndrome", "dry_bite",                          # targets / ground truth
    "order_violations", "n_assumed_onsets", "n_unknown_onsets",       # simulator diagnostics
    "lat", "lon", "month",                                            # placeholders until Phase 3
})
FORBIDDEN_PREFIXES: tuple[str, ...] = ("onset_",)                     # patients.csv onset columns
CONTEXT_FEATURE_NAMES: tuple[str, ...] = ("hour_sin", "hour_cos", "hour_missing", "indoor", "asleep")
SYMPTOM_GROUPS: dict[str, frozenset[str]] = {
    "local": frozenset({"local"}),
    # Systemic = every non-local marker, including non-specific systemic symptoms (marker `none`:
    # abdominal pain, vomiting, headache).
    "systemic": frozenset({"neurotoxic", "haemotoxic", "none"}),
}


class LeakageError(ValueError):
    """A forbidden or unknown column was requested as a model input."""


def select_allowed(patients: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Copy of `patients[columns]`, refusing any column not on the input allowlist."""
    columns = list(columns)
    for col in columns:
        if col in FORBIDDEN_COLUMNS or col.startswith(FORBIDDEN_PREFIXES):
            raise LeakageError(f"column {col!r} is forbidden as a model input")
        if col not in ALLOWED_INPUT_COLUMNS | ALLOWED_CONTEXT_COLUMNS:
            raise LeakageError(f"column {col!r} is not on the model-input allowlist")
    return patients.loc[:, columns].copy()


@dataclass(frozen=True)
class ModelInputs:
    """Everything a model may see, per patient (index aligned with the dataset)."""

    sequences: tuple[np.ndarray, ...]   # (k, 2): symptom index, onset hours; sorted by onset
    presentation: np.ndarray            # hours from bite to presentation (NaN = unknown)
    context: pd.DataFrame               # allowed context columns only
    symptoms: tuple[str, ...]           # vocabulary
    markers: dict[str, str] = field(default_factory=dict)  # symptom -> marker (knowledge table)

    def __len__(self) -> int:
        return len(self.sequences)

    @property
    def n_observed(self) -> np.ndarray:
        return np.array([len(s) for s in self.sequences])

    def subset_symptoms(self, keep: frozenset[int]) -> "ModelInputs":
        seqs = tuple(s[np.isin(s[:, 0].astype(int), list(keep))] if len(s) else s for s in self.sequences)
        return replace(self, sequences=seqs)


def build_inputs(ds: "SymptomDataset", context_columns: Sequence[str] = DEFAULT_CONTEXT_COLUMNS) -> ModelInputs:
    """The only bridge from a dataset to model inputs."""
    base = select_allowed(ds.patients, ["presentation_hours"])
    context = select_allowed(ds.patients, context_columns)
    return ModelInputs(
        sequences=tuple(np.array(s, dtype=np.float64, copy=True) for s in ds.sequences),
        presentation=base["presentation_hours"].to_numpy(dtype=float).copy(),
        context=context.reset_index(drop=True),
        symptoms=tuple(ds.symptoms),
        markers=dict(ds.markers),
    )


@dataclass(frozen=True)
class FeatureSpec:
    """Which input blocks a model sees. The default is the full Phase 2 symptom model."""

    symptoms: bool = True            # False: no symptom features at all (context-only baseline)
    symptom_identity: bool = True    # False: temporal-only representation (see tabular_matrix)
    presence: bool = True
    onset: bool = True
    elapsed: bool = True             # time from onset to presentation
    presentation: bool = True
    n_observed: bool = True
    context: bool = False
    drop_symptoms: tuple[str, ...] = ()
    drop_groups: tuple[str, ...] = ()  # "local" and/or "systemic"
    max_events: int = 6              # temporal-only: number of event slots

    @classmethod
    def from_dict(cls, values: dict[str, Any] | None) -> "FeatureSpec":
        values = dict(values or {})
        known = {f.name for f in fields(cls)}
        unknown = set(values) - known
        if unknown:
            raise ValueError(f"unknown feature options: {sorted(unknown)}")
        for key in ("drop_symptoms", "drop_groups"):
            if key in values:
                values[key] = tuple(values[key])
        return cls(**values)

    def check(self, symptoms: Sequence[str]) -> None:
        unknown = set(self.drop_symptoms) - set(symptoms)
        if unknown:
            raise ValueError(f"drop_symptoms not in vocabulary: {sorted(unknown)}")
        bad_groups = set(self.drop_groups) - set(SYMPTOM_GROUPS)
        if bad_groups:
            raise ValueError(f"drop_groups must be from {sorted(SYMPTOM_GROUPS)}")
        if self.symptoms and self.elapsed and not self.presentation:
            raise ValueError("elapsed time (presentation - onset) reveals the presentation time; "
                             "disable `elapsed` when `presentation` is disabled")
        if self.symptoms and self.symptom_identity and not (self.presence or self.onset or self.elapsed):
            raise ValueError("symptom features need at least one of presence, onset, elapsed")
        if self.symptoms and not self.symptom_identity and not (self.onset or self.elapsed):
            raise ValueError("temporal-only features need onset or elapsed")
        if self.max_events < 1:
            raise ValueError("max_events must be >= 1")


def dropped_indices(spec: FeatureSpec, inputs: ModelInputs) -> frozenset[int]:
    """Vocabulary indices removed from the input by `drop_symptoms` / `drop_groups`."""
    spec.check(inputs.symptoms)
    markers = {m for g in spec.drop_groups for m in SYMPTOM_GROUPS[g]}
    if markers and not inputs.markers:
        raise ValueError("drop_groups needs symptom markers")
    return frozenset(
        i for i, s in enumerate(inputs.symptoms)
        if s in spec.drop_symptoms or inputs.markers.get(s) in markers
    )


def apply_spec(inputs: ModelInputs, spec: FeatureSpec) -> ModelInputs:
    """Inputs with dropped symptoms removed (as if never reported)."""
    drop = dropped_indices(spec, inputs)
    if not drop:
        return inputs
    return inputs.subset_symptoms(frozenset(range(len(inputs.symptoms))) - drop)


def context_matrix(context: pd.DataFrame) -> np.ndarray:
    """(n, 5): cyclic hour of day (0 if unknown), hour-missing flag, indoor, asleep (NaN if unknown)."""
    hours = pd.to_numeric(context["hour_of_day"], errors="coerce").to_numpy(dtype=float)
    missing = np.isnan(hours)
    angle = 2 * np.pi * np.nan_to_num(hours) / 24.0
    flags = [_flag(context[c]) for c in ("indoor", "asleep")]
    return np.column_stack([
        np.where(missing, 0.0, np.sin(angle)), np.where(missing, 0.0, np.cos(angle)), missing.astype(float), *flags,
    ])


def _flag(column: pd.Series) -> np.ndarray:
    mapped = column.map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})
    return mapped.to_numpy(dtype=float)


def tabular_matrix(inputs: ModelInputs, spec: FeatureSpec = FeatureSpec()) -> tuple[np.ndarray, list[str]]:
    """Fixed-width feature matrix and column names; names are validated against the allowlist.

    Symptom identity on (default): per symptom `present_<s>` (0/1), `onset_<s>` and `since_<s>`
    (hours, NaN if not observed). Temporal-only (`symptom_identity=False`): the first
    `max_events` observed events sorted by onset, as `event<j>_onset` / `event<j>_since`
    (NaN-padded), with no information about which symptom each event is.
    """
    spec.check(inputs.symptoms)
    inputs = apply_spec(inputs, spec)
    n, k = len(inputs), len(inputs.symptoms)
    presentation = inputs.presentation.astype(float)
    blocks: list[np.ndarray] = []
    names: list[str] = []

    if spec.symptoms and spec.symptom_identity:
        present = np.zeros((n, k))
        onset = np.full((n, k), np.nan)
        for i, seq in enumerate(inputs.sequences):
            idx = seq[:, 0].astype(int)
            present[i, idx] = 1.0
            onset[i, idx] = seq[:, 1]
        since = presentation[:, None] - onset
        for flag, block, prefix in ((spec.presence, present, "present"), (spec.onset, onset, "onset"),
                                    (spec.elapsed, since, "since")):
            if flag:
                blocks.append(block)
                names += [f"{prefix}_{s}" for s in inputs.symptoms]
    elif spec.symptoms:
        m = spec.max_events
        onset = np.full((n, m), np.nan)
        for i, seq in enumerate(inputs.sequences):
            times = np.sort(seq[:, 1])[:m]
            onset[i, :len(times)] = times
        since = presentation[:, None] - onset
        if spec.onset:
            blocks.append(onset)
            names += [f"event{j}_onset" for j in range(m)]
        if spec.elapsed:
            blocks.append(since)
            names += [f"event{j}_since" for j in range(m)]

    if spec.presentation:
        blocks.append(presentation[:, None])
        names.append("presentation_hours")
    if spec.symptoms and spec.n_observed:
        blocks.append(inputs.n_observed[:, None].astype(float))
        names.append("n_observed")
    if spec.context:
        blocks.append(context_matrix(inputs.context))
        names += list(CONTEXT_FEATURE_NAMES)
    if not blocks:
        raise ValueError("feature spec selects no features")
    validate_feature_names(names, inputs.symptoms, spec.max_events)
    return np.hstack(blocks), names


def allowed_feature_names(symptoms: Sequence[str], max_events: int = 6) -> frozenset[str]:
    per_symptom = {f"{p}_{s}" for p in ("present", "onset", "since") for s in symptoms}
    per_event = {f"event{j}_{t}" for j in range(max_events) for t in ("onset", "since")}
    return frozenset(per_symptom | per_event | {"presentation_hours", "n_observed"} | set(CONTEXT_FEATURE_NAMES))


_TARGET_PATTERN = re.compile(r"species|syndrome|dry_bite|split|patient_id|violation|assumed|unknown|lat$|lon$|month")


def validate_feature_names(names: Sequence[str], symptoms: Sequence[str], max_events: int = 6) -> None:
    """Raise LeakageError if any feature name is not on the allowlist or looks target-derived."""
    allowed = allowed_feature_names(symptoms, max_events)
    if len(set(names)) != len(names):
        raise LeakageError("duplicate feature names")
    for name in names:
        if name not in allowed:
            raise LeakageError(f"feature {name!r} is not on the feature allowlist")
        if name.split("_", 1)[0] not in {"present", "onset", "since"} and _TARGET_PATTERN.search(name):
            raise LeakageError(f"feature {name!r} looks target-derived")
