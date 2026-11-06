"""Model-ready view of a simulated dataset (Phase 2). All data here is SIMULATION data.

    ds = load_dataset("data/processed/sim_v2")

The model input is what a clinician could know at presentation:
- the observed symptom events (`observed=True` in events.csv): symptoms with a known onset
  at or before presentation. Label-only events (`onset_unknown`) and events after
  presentation are never part of the input; they only shape the label.
- `presentation_hours` (time from bite to presentation): the absence of a symptom means
  more the later a patient presents.
- optionally the context flags (hour of day, indoor, asleep). GPS and month are uniform
  placeholders until the Phase 3 geo prior, so they are never used here.

Labels are `venom_syndrome` (from the full course) and `species`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.simulator import SYNDROMES

REPO_ROOT = Path(__file__).resolve().parents[2]
SPLITS: tuple[str, ...] = ("train", "calibration", "test")
CONTEXT_FEATURES: tuple[str, ...] = ("hour_sin", "hour_cos", "hour_missing", "indoor", "asleep")


@dataclass(frozen=True)
class SymptomDataset:
    """Patients of one simulated dataset, with observed events as per-patient sequences."""

    patients: pd.DataFrame          # one row per patient, index 0..n-1 aligned with `sequences`
    sequences: list[np.ndarray]     # per patient: (k, 2) array of (symptom index, onset hours), by onset
    symptoms: tuple[str, ...]       # symptom vocabulary (index = position)
    species: tuple[str, ...]        # species vocabulary
    meta: dict

    @property
    def syndrome_index(self) -> np.ndarray:
        return encode(self.patients["venom_syndrome"], SYNDROMES)

    @property
    def species_index(self) -> np.ndarray:
        return encode(self.patients["species"], self.species)

    def split_mask(self, split: str) -> np.ndarray:
        return (self.patients["split"] == split).to_numpy()


def encode(values: pd.Series, vocabulary: tuple[str, ...]) -> np.ndarray:
    """Index of each value in `vocabulary`; unknown values raise."""
    lookup = {v: i for i, v in enumerate(vocabulary)}
    unknown = sorted(set(values) - set(lookup))
    if unknown:
        raise ValueError(f"values not in vocabulary: {unknown}")
    return values.map(lookup).to_numpy(dtype=np.int64)


def observed_events(events: pd.DataFrame) -> pd.DataFrame:
    """Events the model may see: observed by presentation, with a known onset time."""
    keep = events["observed"].astype(bool) & ~events["onset_unknown"].astype(bool) & events["hours"].notna()
    return events.loc[keep, ["patient_id", "symptom", "hours"]]


def build_sequences(
    events: pd.DataFrame, n_patients: int, symptoms: tuple[str, ...]
) -> list[np.ndarray]:
    """Per patient, a (k, 2) float array of (symptom index, onset hours) sorted by onset."""
    seen = observed_events(events).copy()
    seen["index"] = encode(seen["symptom"], symptoms)
    seen = seen.sort_values(["patient_id", "hours", "index"], kind="stable")
    empty = np.zeros((0, 2), dtype=np.float64)
    sequences = [empty] * n_patients
    for pid, group in seen.groupby("patient_id", sort=False):
        sequences[int(pid)] = group[["index", "hours"]].to_numpy(dtype=np.float64)
    return sequences


def resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def vocabularies(knowledge_dir: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    symptoms = pd.read_csv(knowledge_dir / "symptoms.csv")["symptom"].astype(str)
    species = pd.read_csv(knowledge_dir / "species.csv")["species"].astype(str)
    return tuple(symptoms), tuple(species)


def load_dataset(directory: str | Path) -> SymptomDataset:
    """Load patients.csv, events.csv and meta.json written by `src.data.generate`."""
    directory = resolve(directory)
    meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
    patients = pd.read_csv(directory / "patients.csv")
    events = pd.read_csv(directory / "events.csv")
    if not (patients["patient_id"].to_numpy() == np.arange(len(patients))).all():
        raise ValueError("patients.csv must have patient_id 0..n-1 in order")
    symptoms, species = vocabularies(resolve(meta["config"].get("knowledge_dir", "knowledge")))
    sequences = build_sequences(events, len(patients), symptoms)
    return SymptomDataset(patients, sequences, symptoms, species, meta)


def context_features(patients: pd.DataFrame) -> np.ndarray:
    """(n, 5) context features: cyclic hour of day (0 if unknown), hour-missing flag,
    indoor and asleep (NaN if unknown; XGBoost handles missing values)."""
    hours = pd.to_numeric(patients["hour_of_day"], errors="coerce").to_numpy(dtype=float)
    missing = np.isnan(hours)
    angle = 2 * np.pi * np.nan_to_num(hours) / 24.0
    flags = [_flag(patients[c]) for c in ("indoor", "asleep")]
    return np.column_stack([
        np.where(missing, 0.0, np.sin(angle)), np.where(missing, 0.0, np.cos(angle)), missing.astype(float), *flags,
    ])


def _flag(column: pd.Series) -> np.ndarray:
    mapped = column.map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})
    return mapped.to_numpy(dtype=float)


def tabular_features(ds: SymptomDataset, use_context: bool = False) -> tuple[np.ndarray, list[str]]:
    """Fixed-width features for tree models, built from the observed events only.

    Per symptom: present (0/1), onset hours and hours since onset (NaN if not observed).
    Plus presentation hours, number of observed symptoms and, optionally, context.
    """
    n, k = len(ds.sequences), len(ds.symptoms)
    present = np.zeros((n, k))
    onset = np.full((n, k), np.nan)
    for i, seq in enumerate(ds.sequences):
        idx = seq[:, 0].astype(int)
        present[i, idx] = 1.0
        onset[i, idx] = seq[:, 1]
    presentation = ds.patients["presentation_hours"].to_numpy(dtype=float)
    since = presentation[:, None] - onset
    columns = [present, onset, since, presentation[:, None], present.sum(axis=1, keepdims=True)]
    names = (
        [f"present_{s}" for s in ds.symptoms] + [f"onset_{s}" for s in ds.symptoms]
        + [f"since_{s}" for s in ds.symptoms] + ["presentation_hours", "n_observed"]
    )
    if use_context:
        columns.append(context_features(ds.patients))
        names += list(CONTEXT_FEATURES)
    return np.hstack(columns), names


def validation_split(train_mask: np.ndarray, fraction: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Carve a validation subset out of the training split (for early stopping) so the
    calibration split stays untouched for Phase 6 conformal prediction."""
    if not 0 < fraction < 1:
        raise ValueError("validation fraction must be in (0, 1)")
    train_idx = np.flatnonzero(train_mask)
    rng = np.random.default_rng([seed, 2])
    val_idx = rng.choice(train_idx, size=max(1, int(round(fraction * len(train_idx)))), replace=False)
    val = np.zeros_like(train_mask, dtype=bool)
    val[val_idx] = True
    return train_mask & ~val, val
