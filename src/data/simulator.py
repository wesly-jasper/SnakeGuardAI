"""Synthetic snakebite patient simulator.

Samples patients from the literature-derived knowledge base (src/data/knowledge.py).
Everything produced here is SIMULATED data and any result computed from it must be
labelled as a simulation result.

Each patient gets a full symptom course; the venom-syndrome label is derived from the
whole course, while the model only sees events up to presentation (`observed_events`).

Placeholders until later phases:
- GPS is uniform over India's bounding box and month is uniform. The real
  P(species | location, month) prior comes from GBIF occurrences in Phase 3.
- Context features (night, indoor, asleep) are sampled independently per species.

Time to presentation is drawn from `presentation_delay`, a cited piecewise-uniform
distribution (src/data/presentation.py); without one it is uniform over
`presentation_hours_range`.

Dependence between symptoms (modelling assumption, varied in the sensitivity analysis):
a latent severity z ~ N(0, 1) per patient enters a Gaussian copula with correlation
`severity_correlation` (rho). Higher severity makes every symptom more likely and its onset
earlier within its window, while each symptom's marginal frequency and onset window stay
exactly as cited (onset is uniform in the window over all draws; among patients who have
a symptom it is skewed earlier when rho > 0, because they are more often severe).
rho = 0 gives independent symptoms. Cited onset orders
(knowledge/onset_order.csv) then push a later sign to no earlier than the sign before it,
capped at its own window maximum.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.special import ndtr, ndtri

from src.data.knowledge import ALL_SPECIES, KnowledgeBase
from src.data.presentation import DelayDistribution

SYNDROMES: tuple[str, ...] = ("neurotoxic", "haemotoxic", "local-only", "non-venomous/dry")
DRY_LABEL = "non-venomous/dry"
LOCAL_LABEL = "local-only"
# Haemotoxic wins over neurotoxic: Russell's viper can cause both, and coagulopathy
# drives the triage pathway. Open decision, see docs/phase1_plan.md.
DEFAULT_PRECEDENCE: tuple[str, ...] = ("haemotoxic", "neurotoxic")

# Rough bounding box of India (lat, lon). Placeholder until the Phase 3 geo prior.
INDIA_LAT_RANGE: tuple[float, float] = (6.5, 35.5)
INDIA_LON_RANGE: tuple[float, float] = (68.0, 97.5)
DAY_HOURS: tuple[float, float] = (6.0, 18.0)


@dataclass(frozen=True)
class SymptomEvent:
    symptom: str
    hours: float


@dataclass(frozen=True)
class SyntheticPatient:
    species: str
    venom_syndrome: str
    dry_bite: bool
    course: tuple[SymptomEvent, ...]
    presentation_hours: float
    lat: float
    lon: float
    month: int
    hour_of_day: float | None
    indoor: bool | None
    asleep: bool | None

    @property
    def observed_events(self) -> tuple[SymptomEvent, ...]:
        """Events visible to the model: those at or before presentation."""
        return tuple(e for e in self.course if e.hours <= self.presentation_hours)


@dataclass(frozen=True)
class SpeciesSpec:
    """Everything needed to sample one species, as arrays."""

    species: str
    venomous: bool
    dry_bite_rate: float
    symptoms: tuple[str, ...]
    onset_min: np.ndarray
    onset_max: np.ndarray
    frequency: np.ndarray
    context: dict[str, float]
    order: tuple[tuple[int, int], ...] = ()


def fill_onsets(
    clinical: pd.DataFrame, fallback: tuple[float, float] | None
) -> pd.DataFrame:
    """Fill blank onset bounds from `fallback` (lo, hi); without one, drop such rows."""
    blank = clinical[["onset_min_hours", "onset_max_hours"]].isna()
    if fallback is None:
        return clinical[~blank.any(axis=1)]
    filled = clinical.copy()
    filled["onset_min_hours"] = filled["onset_min_hours"].fillna(fallback[0])
    filled["onset_max_hours"] = filled["onset_max_hours"].fillna(fallback[1])
    filled["onset_max_hours"] = filled[["onset_min_hours", "onset_max_hours"]].max(axis=1)
    return filled


def count_fallback_rows(kb: KnowledgeBase) -> int:
    """Positive-frequency clinical rows with at least one blank onset bound."""
    active = kb.clinical[kb.clinical["frequency"] > 0]
    return int(active[["onset_min_hours", "onset_max_hours"]].isna().any(axis=1).sum())


def order_pairs(
    onset_order: pd.DataFrame, species: str, symptoms: tuple[str, ...]
) -> tuple[tuple[int, int], ...]:
    """(before, after) index pairs into `symptoms` that apply to `species`."""
    index = {s: i for i, s in enumerate(symptoms)}
    rules = onset_order[onset_order["species"].isin([species, ALL_SPECIES])]
    return tuple(
        (index[r.before], index[r.after])
        for r in rules.itertuples()
        if r.before in index and r.after in index
    )


def apply_order(
    onsets: np.ndarray, present: np.ndarray, onset_max: np.ndarray, order: tuple[tuple[int, int], ...]
) -> np.ndarray:
    """Delay each `after` sign to no earlier than its `before` sign, capped at its window max."""
    onsets = onsets.copy()
    for _ in range(len(order)):  # enough passes to propagate along any chain
        changed = False
        for before, after in order:
            if present[before] and present[after] and onsets[after] < onsets[before]:
                onsets[after] = min(onsets[before], onset_max[after])
                changed = True
        if not changed:
            break
    return onsets


def build_specs(
    kb: KnowledgeBase, onset_fallback: tuple[float, float] | None = None
) -> dict[str, SpeciesSpec]:
    """One SpeciesSpec per usable species, sorted by name.

    Venomous species without clinical rows are skipped (they could only produce
    mislabelled all-dry patients); non-venomous species may have no rows. Blank onset
    bounds are filled from `onset_fallback`, or the row is dropped when it is None.
    """
    clinical = fill_onsets(kb.clinical[kb.clinical["frequency"] > 0], onset_fallback)
    specs: dict[str, SpeciesSpec] = {}
    skipped = []
    for row in kb.species.sort_values("species").itertuples():
        rows = clinical[clinical["species"] == row.species]
        venomous = row.group == "venomous"
        if venomous and rows.empty:
            skipped.append(row.species)
            continue
        ctx = kb.context[kb.context["species"] == row.species]
        symptoms = tuple(rows["symptom"])
        specs[row.species] = SpeciesSpec(
            species=row.species,
            venomous=venomous,
            dry_bite_rate=float(row.dry_bite_rate) if venomous and pd.notna(row.dry_bite_rate) else 0.0,
            symptoms=symptoms,
            onset_min=rows["onset_min_hours"].to_numpy(dtype=float),
            onset_max=rows["onset_max_hours"].to_numpy(dtype=float),
            frequency=rows["frequency"].to_numpy(dtype=float),
            context=dict(zip(ctx["feature"], ctx["probability"].astype(float))),
            order=order_pairs(kb.onset_order, row.species, symptoms),
        )
    if skipped:
        warnings.warn(f"skipping venomous species with no clinical rows: {skipped}", stacklevel=2)
    return specs


def derive_syndrome(
    symptoms: Iterable[str],
    marker_of: dict[str, str],
    venomous: bool,
    precedence: Sequence[str] = DEFAULT_PRECEDENCE,
) -> str:
    """Eventual venom syndrome from the symptoms of a full course.

    Non-venomous species and symptomless courses are `non-venomous/dry`. Otherwise the
    first marker in `precedence` that occurs wins; envenoming without a neurotoxic or
    haemotoxic marker is `local-only`.
    """
    symptoms = list(symptoms)
    if not venomous or not symptoms:
        return DRY_LABEL
    markers = {marker_of[s] for s in symptoms}
    for marker in precedence:
        if marker in markers:
            return marker
    return LOCAL_LABEL


def sample_course(
    spec: SpeciesSpec, rng: np.random.Generator, severity_correlation: float = 0.0
) -> tuple[bool, tuple[SymptomEvent, ...]]:
    """Return (dry_bite, full symptom course sorted by onset).

    Presence and onset position use a Gaussian copula on a shared severity (see module
    docstring); marginals equal the table's frequency and a uniform draw in the window.
    """
    if not 0.0 <= severity_correlation <= 1.0:
        raise ValueError("severity_correlation must be within [0, 1]")
    k = len(spec.symptoms)
    dry = spec.venomous and bool(rng.random() < spec.dry_bite_rate)
    severity = rng.standard_normal()
    shared, own = np.sqrt(severity_correlation), np.sqrt(1.0 - severity_correlation)
    presence_latent = shared * severity + own * rng.standard_normal(k)
    with np.errstate(divide="ignore"):
        present = presence_latent > ndtri(1.0 - spec.frequency)
    position = ndtr(-(shared * severity + own * rng.standard_normal(k)))  # severe -> early
    onsets = spec.onset_min + position * (spec.onset_max - spec.onset_min)
    onsets = apply_order(onsets, present, spec.onset_max, spec.order)
    if dry:
        return True, ()
    events = sorted(
        (SymptomEvent(s, float(h)) for s, h, keep in zip(spec.symptoms, onsets, present) if keep),
        key=lambda e: e.hours,
    )
    return False, tuple(events)


def sample_context(
    context: dict[str, float], rng: np.random.Generator
) -> tuple[float | None, bool | None, bool | None]:
    """Sample (hour_of_day, indoor, asleep); None where the species has no cited value."""
    draws = rng.random(3)
    flags = [
        bool(draws[i] < context[f]) if f in context else None
        for i, f in enumerate(("night", "indoor", "asleep"))
    ]
    night = flags[0]
    hour_draw = float(rng.uniform(0.0, 12.0))
    if night is None:
        hour = None
    elif night:
        hour = (DAY_HOURS[1] + hour_draw) % 24.0
    else:
        hour = DAY_HOURS[0] + hour_draw
    return hour, flags[1], flags[2]


def simulate_patient(
    spec: SpeciesSpec,
    rng: np.random.Generator,
    marker_of: dict[str, str],
    presentation_hours_range: tuple[float, float] = (0.5, 24.0),
    precedence: Sequence[str] = DEFAULT_PRECEDENCE,
    severity_correlation: float = 0.0,
    presentation_delay: DelayDistribution | None = None,
) -> SyntheticPatient:
    """Sample one patient bitten by `spec.species`."""
    delay = presentation_delay or DelayDistribution.uniform(*presentation_hours_range)
    dry, course = sample_course(spec, rng, severity_correlation)
    hour, indoor, asleep = sample_context(spec.context, rng)
    return SyntheticPatient(
        species=spec.species,
        venom_syndrome=derive_syndrome((e.symptom for e in course), marker_of, spec.venomous, precedence),
        dry_bite=dry,
        course=course,
        presentation_hours=delay.sample(rng),
        lat=float(rng.uniform(*INDIA_LAT_RANGE)),
        lon=float(rng.uniform(*INDIA_LON_RANGE)),
        month=int(rng.integers(1, 13)),
        hour_of_day=hour,
        indoor=indoor,
        asleep=asleep,
    )


def species_probabilities(
    species: list[str], weights: dict[str, float] | None
) -> np.ndarray:
    """Normalised sampling probabilities; uniform when `weights` is None."""
    if weights is None:
        return np.full(len(species), 1.0 / len(species))
    unknown = set(weights) - set(species)
    if unknown:
        raise ValueError(f"weights given for species not in table: {sorted(unknown)}")
    probs = np.array([weights.get(s, 0.0) for s in species], dtype=float)
    if probs.sum() <= 0:
        raise ValueError("species_weights must have a positive sum")
    return probs / probs.sum()


def simulate_patients(
    kb: KnowledgeBase,
    n: int,
    seed: int,
    species_weights: dict[str, float] | None = None,
    presentation_hours_range: tuple[float, float] = (0.5, 24.0),
    precedence: Sequence[str] = DEFAULT_PRECEDENCE,
    onset_fallback: tuple[float, float] | None = None,
    severity_correlation: float = 0.0,
    presentation_delay: DelayDistribution | None = None,
) -> list[SyntheticPatient]:
    """Sample `n` synthetic patients. Species are uniform unless weights are given."""
    specs = build_specs(kb, onset_fallback)
    if not specs:
        warnings.warn("knowledge base has no usable species; returning no patients", stacklevel=2)
        return []
    rng = np.random.default_rng(seed)
    species = list(specs)
    picks = rng.choice(len(species), size=n, p=species_probabilities(species, species_weights))
    marker_of = kb.marker_of()
    return [
        simulate_patient(
            specs[species[i]], rng, marker_of, presentation_hours_range, precedence, severity_correlation,
            presentation_delay,
        )
        for i in picks
    ]


def assign_splits(n: int, fractions: dict[str, float], seed: int) -> np.ndarray:
    """Randomly assign each of `n` patients to a split with the given fractions."""
    names = list(fractions)
    probs = np.array([fractions[k] for k in names], dtype=float)
    if (probs < 0).any() or not np.isclose(probs.sum(), 1.0):
        raise ValueError("split fractions must be non-negative and sum to 1")
    counts = np.floor(probs * n).astype(int)
    counts[0] += n - counts.sum()
    labels = np.repeat(np.array(names, dtype=object), counts)
    return np.random.default_rng([seed, 1]).permutation(labels)


def to_dataframe(patients: list[SyntheticPatient]) -> pd.DataFrame:
    """One row per patient, with observed `onset_<symptom>` columns (NaN if not seen)."""
    records = []
    for pid, p in enumerate(patients):
        record: dict[str, object] = {
            "patient_id": pid,
            "species": p.species,
            "venom_syndrome": p.venom_syndrome,
            "dry_bite": p.dry_bite,
            "presentation_hours": p.presentation_hours,
            "lat": p.lat,
            "lon": p.lon,
            "month": p.month,
            "hour_of_day": p.hour_of_day,
            "indoor": p.indoor,
            "asleep": p.asleep,
        }
        record.update({f"onset_{e.symptom}": e.hours for e in p.observed_events})
        records.append(record)
    return pd.DataFrame.from_records(records)


def events_dataframe(patients: list[SyntheticPatient]) -> pd.DataFrame:
    """Long format: one row per course event, with `observed` = seen by presentation."""
    rows = [
        (pid, e.symptom, e.hours, e.hours <= p.presentation_hours)
        for pid, p in enumerate(patients)
        for e in p.course
    ]
    return pd.DataFrame(rows, columns=["patient_id", "symptom", "hours", "observed"])
