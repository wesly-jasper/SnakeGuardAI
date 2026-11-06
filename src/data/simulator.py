"""Synthetic snakebite patient simulator.

Samples patients from the literature-derived knowledge base (src/data/knowledge.py).
Everything produced here is SIMULATED data and any result computed from it must be
labelled as a simulation result.

Each patient gets a full symptom course; the venom-syndrome label is derived from the
whole course, while the model only sees events up to presentation (`observed_events`).

Placeholders until later phases:
- GPS is uniform over India's bounding box and month is uniform. The real
  P(species | location, month) prior comes from GBIF occurrences in Phase 3.

Context (night, indoor, asleep): sampled jointly from cited complete-case counts
(knowledge/context_joint.csv) where a species has them; otherwise each feature is drawn
independently from its cited marginal (knowledge/context_table.csv).

Time to presentation is drawn from `presentation_delay`, a cited piecewise-uniform
distribution (src/data/presentation.py); without one it is uniform over
`presentation_hours_range`.

Onset windows: rows with a cited window are used as cited. Rows whose window is unknown are
dropped unless an `onset_fallback` window is given; fallback onsets are an ASSUMPTION and
every event they produce carries `onset_assumed=True`.

Dependence between symptoms (modelling assumption, varied in the sensitivity analysis):
a latent severity z ~ N(0, 1) per patient enters a Gaussian copula with correlation
`severity_correlation` (rho). Higher severity makes every symptom more likely and its onset
earlier within its window, while each symptom's marginal frequency and onset window stay
as cited (onset is uniform in the window over all draws before ordering; among patients who
have a symptom it is skewed earlier when rho > 0, because they are more often severe).
rho = 0 gives independent symptoms.

Cited onset orders (knowledge/onset_order.csv): a later sign is pushed to no earlier than
the sign before it, capped at its own window maximum. Where windows only partly overlap the
push cannot always succeed; the onset times are then redrawn (same severity and presence)
up to `max_order_tries` times, which conditions the onsets on the order. A patient still
violating an order after that keeps the draw and is flagged (`order_violations` > 0); the
order is never reported as satisfied when it is not. Windows that make an order impossible
whenever both signs occur raise an error. Ordering and redraws shift the onset marginals;
src/data/diagnostics.py measures by how much.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.special import ndtr, ndtri

from src.data.knowledge import JOINT_FEATURES, KnowledgeBase, order_edges
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
DEFAULT_MAX_ORDER_TRIES = 100
ORDER_TOLERANCE = 1e-9

Cell = tuple[bool, bool, bool]


@dataclass(frozen=True)
class SymptomEvent:
    symptom: str
    hours: float
    onset_assumed: bool = False  # True when the onset came from the fallback window


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
    order_violations: int = 0

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
    onset_assumed: np.ndarray | None = None
    joint_context: tuple[tuple[Cell, ...], np.ndarray] | None = None


@dataclass(frozen=True)
class CourseDraw:
    """One sampled course with its pre-order onsets, for diagnostics."""

    dry: bool
    present: np.ndarray
    raw_onsets: np.ndarray  # first draw, before ordering
    onsets: np.ndarray  # final, after ordering (and any redraws)
    order_violations: int
    order_redraws: int


def fill_onsets(
    clinical: pd.DataFrame, fallback: tuple[float, float] | None
) -> pd.DataFrame:
    """Fill blank onset bounds from `fallback` (lo, hi); without one, drop such rows.

    Adds `onset_assumed` (True where any bound came from the fallback).
    """
    blank = clinical[["onset_min_hours", "onset_max_hours"]].isna().any(axis=1)
    if fallback is None:
        return clinical[~blank].assign(onset_assumed=False)
    filled = clinical.copy()
    filled["onset_min_hours"] = filled["onset_min_hours"].fillna(fallback[0])
    filled["onset_max_hours"] = filled["onset_max_hours"].fillna(fallback[1])
    filled["onset_max_hours"] = filled[["onset_min_hours", "onset_max_hours"]].max(axis=1)
    return filled.assign(onset_assumed=blank)


def count_fallback_rows(kb: KnowledgeBase) -> int:
    """Positive-frequency clinical rows with at least one blank onset bound."""
    active = kb.clinical[kb.clinical["frequency"] > 0]
    return int(active[["onset_min_hours", "onset_max_hours"]].isna().any(axis=1).sum())


def order_pairs(
    onset_order: pd.DataFrame, species: str, symptoms: tuple[str, ...]
) -> tuple[tuple[int, int], ...]:
    """(before, after) index pairs into `symptoms` that apply to `species`."""
    index = {s: i for i, s in enumerate(symptoms)}
    return tuple(
        (index[b], index[a]) for b, a in order_edges(onset_order, species) if b in index and a in index
    )


def apply_order(
    onsets: np.ndarray, present: np.ndarray, onset_max: np.ndarray, order: tuple[tuple[int, int], ...]
) -> np.ndarray:
    """Delay each `after` sign to no earlier than its `before` sign, capped at its window max.

    The cap can leave an order violated; use `count_order_violations` to check.
    """
    onsets = onsets.copy()
    for _ in range(len(order) + 1):  # enough passes to propagate along any acyclic chain
        changed = False
        for before, after in order:
            if present[before] and present[after] and onsets[after] < onsets[before]:
                new = min(onsets[before], onset_max[after])
                if new != onsets[after]:
                    onsets[after] = new
                    changed = True
        if not changed:
            break
    return onsets


def count_order_violations(
    onsets: np.ndarray, present: np.ndarray, order: tuple[tuple[int, int], ...]
) -> int:
    """Number of order rules broken by this course (both signs present, after < before)."""
    return sum(
        1 for b, a in order
        if present[b] and present[a] and onsets[a] < onsets[b] - ORDER_TOLERANCE
    )


def order_window_status(spec: SpeciesSpec) -> list[dict[str, object]]:
    """Classify every order rule of `spec` by whether its windows allow it.

    - compatible: the push always succeeds
    - partial: some draws cannot be ordered by the push alone (redraws needed)
    - incompatible: the windows make the order impossible whenever the signs involved occur
    The earliest feasible onset of each sign is propagated along the chain of rules
    (assuming every sign in the chain occurs).
    """
    lower = spec.onset_min.astype(float).copy()
    for _ in range(len(spec.order) + 1):
        for b, a in spec.order:
            lower[a] = max(lower[a], lower[b])
    rows = []
    for b, a in spec.order:
        if lower[b] > spec.onset_max[a] or lower[a] > spec.onset_max[a]:
            status = "incompatible"
        elif spec.onset_max[b] > spec.onset_max[a]:
            status = "partial"
        else:
            status = "compatible"
        rows.append({
            "species": spec.species, "before": spec.symptoms[b], "after": spec.symptoms[a],
            "before_window": (float(spec.onset_min[b]), float(spec.onset_max[b])),
            "after_window": (float(spec.onset_min[a]), float(spec.onset_max[a])),
            "status": status,
        })
    return rows


def joint_cells(joint: pd.DataFrame, species: str) -> tuple[tuple[Cell, ...], np.ndarray] | None:
    """(cells, probabilities) of the cited joint context counts for `species`, or None."""
    rows = joint[joint["species"] == species]
    if rows.empty:
        return None
    counts = rows["count"].to_numpy(dtype=float)
    cells = tuple(tuple(bool(v) for v in r) for r in rows[list(JOINT_FEATURES)].itertuples(index=False))
    return cells, counts / counts.sum()


def build_specs(
    kb: KnowledgeBase, onset_fallback: tuple[float, float] | None = None
) -> dict[str, SpeciesSpec]:
    """One SpeciesSpec per usable species, sorted by name.

    Venomous species without clinical rows are skipped (they could only produce
    mislabelled all-dry patients); non-venomous species may have no rows. Blank onset
    bounds are filled from `onset_fallback`, or the row is dropped when it is None.
    Raises if an onset order is impossible given the windows.
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
            onset_assumed=rows["onset_assumed"].to_numpy(dtype=bool),
            joint_context=joint_cells(kb.context_joint, row.species),
        )
    if skipped:
        warnings.warn(f"skipping venomous species with no clinical rows: {skipped}", stacklevel=2)
    bad = [r for spec in specs.values() for r in order_window_status(spec) if r["status"] == "incompatible"]
    if bad:
        raise ValueError(
            "onset order impossible with the onset windows: "
            + "; ".join(f"{r['species']}: {r['before']} {r['before_window']} -> {r['after']} {r['after_window']}" for r in bad)
        )
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


def _check_correlation(severity_correlation: float) -> None:
    if not (math.isfinite(severity_correlation) and 0.0 <= severity_correlation <= 1.0):
        raise ValueError("severity_correlation must be within [0, 1]")


def _draw_onsets(spec: SpeciesSpec, rng: np.random.Generator, shared_term: float, own: float) -> np.ndarray:
    position = ndtr(-(shared_term + own * rng.standard_normal(len(spec.symptoms))))  # severe -> early
    return spec.onset_min + position * (spec.onset_max - spec.onset_min)


def draw_course(
    spec: SpeciesSpec,
    rng: np.random.Generator,
    severity_correlation: float = 0.0,
    max_order_tries: int = DEFAULT_MAX_ORDER_TRIES,
) -> CourseDraw:
    """Sample presence and onsets (copula), then enforce the cited onset order."""
    _check_correlation(severity_correlation)
    if max_order_tries < 1:
        raise ValueError("max_order_tries must be >= 1")
    k = len(spec.symptoms)
    dry = spec.venomous and bool(rng.random() < spec.dry_bite_rate)
    severity = rng.standard_normal()
    shared, own = np.sqrt(severity_correlation), np.sqrt(1.0 - severity_correlation)
    presence_latent = shared * severity + own * rng.standard_normal(k)
    with np.errstate(divide="ignore"):
        present = presence_latent > ndtri(1.0 - spec.frequency)
    raw = _draw_onsets(spec, rng, shared * severity, own)
    onsets = apply_order(raw, present, spec.onset_max, spec.order)
    violations = count_order_violations(onsets, present, spec.order)
    redraws = 0
    while violations and not dry and redraws + 1 < max_order_tries:
        onsets = apply_order(_draw_onsets(spec, rng, shared * severity, own), present, spec.onset_max, spec.order)
        violations = count_order_violations(onsets, present, spec.order)
        redraws += 1
    return CourseDraw(dry, present, raw, onsets, 0 if dry else violations, redraws)


def course_events(spec: SpeciesSpec, draw: CourseDraw) -> tuple[SymptomEvent, ...]:
    """The course's events sorted by onset; empty for a dry bite."""
    if draw.dry:
        return ()
    assumed = spec.onset_assumed if spec.onset_assumed is not None else np.zeros(len(spec.symptoms), bool)
    events = (
        SymptomEvent(s, float(h), bool(a))
        for s, h, keep, a in zip(spec.symptoms, draw.onsets, draw.present, assumed)
        if keep
    )
    return tuple(sorted(events, key=lambda e: e.hours))


def sample_course(
    spec: SpeciesSpec, rng: np.random.Generator, severity_correlation: float = 0.0
) -> tuple[bool, tuple[SymptomEvent, ...]]:
    """Return (dry_bite, full symptom course sorted by onset). See `draw_course`."""
    draw = draw_course(spec, rng, severity_correlation)
    return draw.dry, course_events(spec, draw)


def _hour(night: bool | None, rng: np.random.Generator) -> float | None:
    hour_draw = float(rng.uniform(0.0, 12.0))
    if night is None:
        return None
    return (DAY_HOURS[1] + hour_draw) % 24.0 if night else DAY_HOURS[0] + hour_draw


def sample_context(
    context: dict[str, float],
    rng: np.random.Generator,
    joint: tuple[tuple[Cell, ...], np.ndarray] | None = None,
) -> tuple[float | None, bool | None, bool | None]:
    """Sample (hour_of_day, indoor, asleep); None where the species has no cited value.

    With `joint` cells the three flags are drawn together from the cited counts;
    otherwise each flag is drawn independently from its marginal.
    """
    if joint is not None:
        cells, probs = joint
        night, indoor, asleep = cells[int(rng.choice(len(cells), p=probs))]
        return _hour(night, rng), indoor, asleep
    draws = rng.random(3)
    flags = [
        bool(draws[i] < context[f]) if f in context else None
        for i, f in enumerate(("night", "indoor", "asleep"))
    ]
    return _hour(flags[0], rng), flags[1], flags[2]


def simulate_patient(
    spec: SpeciesSpec,
    rng: np.random.Generator,
    marker_of: dict[str, str],
    presentation_hours_range: tuple[float, float] = (0.5, 24.0),
    precedence: Sequence[str] = DEFAULT_PRECEDENCE,
    severity_correlation: float = 0.0,
    presentation_delay: DelayDistribution | None = None,
    max_order_tries: int = DEFAULT_MAX_ORDER_TRIES,
) -> SyntheticPatient:
    """Sample one patient bitten by `spec.species`."""
    delay = presentation_delay or DelayDistribution.uniform(*presentation_hours_range)
    draw = draw_course(spec, rng, severity_correlation, max_order_tries)
    course = course_events(spec, draw)
    hour, indoor, asleep = sample_context(spec.context, rng, spec.joint_context)
    return SyntheticPatient(
        species=spec.species,
        venom_syndrome=derive_syndrome((e.symptom for e in course), marker_of, spec.venomous, precedence),
        dry_bite=draw.dry,
        course=course,
        presentation_hours=delay.sample(rng),
        lat=float(rng.uniform(*INDIA_LAT_RANGE)),
        lon=float(rng.uniform(*INDIA_LON_RANGE)),
        month=int(rng.integers(1, 13)),
        hour_of_day=hour,
        indoor=indoor,
        asleep=asleep,
        order_violations=draw.order_violations,
    )


def species_probabilities(
    species: list[str], weights: dict[str, float] | None
) -> np.ndarray:
    """Normalised sampling probabilities; uniform when `weights` is None."""
    if not species:
        raise ValueError("no species to sample from")
    if weights is None:
        return np.full(len(species), 1.0 / len(species))
    unknown = set(weights) - set(species)
    if unknown:
        raise ValueError(f"weights given for species not in table: {sorted(unknown)}")
    probs = np.array([weights.get(s, 0.0) for s in species], dtype=float)
    if not np.isfinite(probs).all() or (probs < 0).any():
        raise ValueError("species_weights must be finite and non-negative")
    if probs.sum() <= 0:
        raise ValueError("species_weights must have a positive sum")
    return probs / probs.sum()


def check_count(n: object, name: str = "n") -> int:
    """`n` as a non-negative int; rejects bools, floats and negatives."""
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {n!r}")
    return int(n)


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
    max_order_tries: int = DEFAULT_MAX_ORDER_TRIES,
) -> list[SyntheticPatient]:
    """Sample `n` synthetic patients. Species are uniform unless weights are given."""
    n = check_count(n)
    _check_correlation(severity_correlation)
    if presentation_delay is None:
        DelayDistribution.uniform(*presentation_hours_range)  # validates the range
    specs = build_specs(kb, onset_fallback)
    if not specs:
        raise ValueError("knowledge base has no usable species")
    rng = np.random.default_rng(seed)
    species = list(specs)
    picks = rng.choice(len(species), size=n, p=species_probabilities(species, species_weights))
    marker_of = kb.marker_of()
    return [
        simulate_patient(
            specs[species[i]], rng, marker_of, presentation_hours_range, precedence, severity_correlation,
            presentation_delay, max_order_tries,
        )
        for i in picks
    ]


def assign_splits(n: int, fractions: dict[str, float], seed: int) -> np.ndarray:
    """Randomly assign each of `n` patients to a split with the given fractions."""
    n = check_count(n)
    names = list(fractions)
    probs = np.array([fractions[k] for k in names], dtype=float)
    if not names or not np.isfinite(probs).all() or (probs < 0).any() or not np.isclose(probs.sum(), 1.0):
        raise ValueError("split fractions must be finite, non-negative and sum to 1")
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
            "order_violations": p.order_violations,
            "n_assumed_onsets": sum(e.onset_assumed for e in p.course),
        }
        record.update({f"onset_{e.symptom}": e.hours for e in p.observed_events})
        records.append(record)
    return pd.DataFrame.from_records(records)


def events_dataframe(patients: list[SyntheticPatient]) -> pd.DataFrame:
    """Long format: one row per course event, with `observed` = seen by presentation and
    `onset_assumed` = onset from the fallback window rather than a cited window."""
    rows = [
        (pid, e.symptom, e.hours, e.hours <= p.presentation_hours, e.onset_assumed)
        for pid, p in enumerate(patients)
        for e in p.course
    ]
    return pd.DataFrame(rows, columns=["patient_id", "symptom", "hours", "observed", "onset_assumed"])
