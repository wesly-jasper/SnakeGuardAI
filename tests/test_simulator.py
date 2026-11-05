"""Tests for src/data/simulator.py. Fixture tables are made up; not clinical data."""

from pathlib import Path

import numpy as np
import pytest

from src.data.knowledge import KnowledgeBase, load_knowledge
from src.data.simulator import (
    DRY_LABEL,
    INDIA_LAT_RANGE,
    INDIA_LON_RANGE,
    LOCAL_LABEL,
    assign_splits,
    derive_syndrome,
    events_dataframe,
    simulate_patients,
    to_dataframe,
)
from tests.conftest import CLINICAL, SPECIES, write_knowledge

MARKERS = {"neuro": "neurotoxic", "haemo": "haemotoxic", "swell": "local", "vomit": "none"}
SPLITS = {"train": 0.6, "calibration": 0.2, "test": 0.2}


@pytest.fixture
def kb(knowledge_dir: Path) -> KnowledgeBase:
    return load_knowledge(knowledge_dir, require_citations=True)


def test_same_seed_is_reproducible(kb: KnowledgeBase) -> None:
    assert simulate_patients(kb, 50, seed=1) == simulate_patients(kb, 50, seed=1)
    assert simulate_patients(kb, 50, seed=1) != simulate_patients(kb, 50, seed=2)


@pytest.mark.parametrize(
    "symptoms, venomous, expected",
    [
        (["neuro", "haemo"], True, "haemotoxic"),
        (["neuro", "vomit"], True, "neurotoxic"),
        (["swell"], True, LOCAL_LABEL),
        (["vomit"], True, LOCAL_LABEL),
        ([], True, DRY_LABEL),
        (["swell", "haemo"], False, DRY_LABEL),
    ],
)
def test_derive_syndrome(symptoms: list[str], venomous: bool, expected: str) -> None:
    assert derive_syndrome(symptoms, MARKERS, venomous) == expected


def test_derive_syndrome_precedence_is_configurable() -> None:
    precedence = ("neurotoxic", "haemotoxic")
    assert derive_syndrome(["neuro", "haemo"], MARKERS, True, precedence) == "neurotoxic"


def test_course_windows_and_censoring(kb: KnowledgeBase) -> None:
    windows = {
        (r.species, r.symptom): (r.onset_min_hours, r.onset_max_hours)
        for r in kb.clinical.itertuples()
    }
    for p in simulate_patients(kb, 500, seed=0):
        hours = [e.hours for e in p.course]
        assert hours == sorted(hours)
        for e in p.course:
            lo, hi = windows[(p.species, e.symptom)]
            assert lo <= e.hours <= hi
        assert all(e.hours <= p.presentation_hours for e in p.observed_events)
        assert set(p.observed_events) <= set(p.course)


def test_label_uses_full_course_not_observed(kb: KnowledgeBase) -> None:
    for p in simulate_patients(kb, 500, seed=0):
        symptoms = {e.symptom for e in p.course}
        assert "never" not in symptoms
        if p.species == "Species a":
            assert p.venom_syndrome == "neurotoxic"
        if p.species == "Species b":
            assert p.venom_syndrome == "haemotoxic"
            # "late" is in the course but always after presentation (max 24 h).
            assert "late" in symptoms
            assert "late" not in {e.symptom for e in p.observed_events}
        if p.species == "Species c":
            assert p.venom_syndrome == DRY_LABEL and not p.dry_bite


def test_frequency_rate(kb: KnowledgeBase) -> None:
    patients = [p for p in simulate_patients(kb, 2000, seed=0) if p.species == "Species a"]
    rate = np.mean(["vomit" in {e.symptom for e in p.course} for p in patients])
    assert 0.44 < rate < 0.56


def test_dry_bites(tmp_path: Path) -> None:
    species = [SPECIES[0][:3] + (1.0,) + SPECIES[0][4:]] + SPECIES[1:]
    kb = load_knowledge(write_knowledge(tmp_path, species=species))
    for p in simulate_patients(kb, 200, seed=0, species_weights={"Species a": 1.0}):
        assert p.species == "Species a"
        assert p.dry_bite and p.course == () and p.venom_syndrome == DRY_LABEL


def test_context(kb: KnowledgeBase) -> None:
    for p in simulate_patients(kb, 300, seed=3):
        assert INDIA_LAT_RANGE[0] <= p.lat <= INDIA_LAT_RANGE[1]
        assert INDIA_LON_RANGE[0] <= p.lon <= INDIA_LON_RANGE[1]
        assert 1 <= p.month <= 12
        assert p.indoor is None  # no cited value for any fixture species
        if p.species == "Species a":
            assert p.hour_of_day is not None and (p.hour_of_day >= 18 or p.hour_of_day < 6)
            assert p.asleep in (True, False)
        if p.species == "Species b":
            assert 6 <= p.hour_of_day < 18 and p.asleep is None
        if p.species == "Species c":
            assert p.hour_of_day is None


def test_onset_fallback(tmp_path: Path) -> None:
    rows = [r for r in CLINICAL if r[0] != "Species b"] + [
        ("Species b", "haemo", None, None, 1.0, "fake2026", "", True),  # no onset at all
        ("Species b", "neuro", None, 2.0, 1.0, "fake2026", "", True),  # upper bound only
    ]
    kb = load_knowledge(write_knowledge(tmp_path, clinical=rows), allow_missing_onset=True)
    with pytest.warns(UserWarning, match="Species b"):
        assert all(p.species != "Species b" for p in simulate_patients(kb, 100, seed=0))
    patients = simulate_patients(kb, 300, seed=0, onset_fallback=(1.0, 5.0))
    for p in (p for p in patients if p.species == "Species b"):
        hours = {e.symptom: e.hours for e in p.course}
        assert 1.0 <= hours["haemo"] <= 5.0
        assert 1.0 <= hours["neuro"] <= 2.0


def test_venomous_species_without_rows_skipped(tmp_path: Path) -> None:
    species = SPECIES + [("Species d", "D", "venomous", 0.0, "fake2026", "", True)]
    kb = load_knowledge(write_knowledge(tmp_path, species=species))
    with pytest.warns(UserWarning, match="Species d"):
        patients = simulate_patients(kb, 100, seed=0)
    assert "Species d" not in {p.species for p in patients}


def test_species_weights(kb: KnowledgeBase) -> None:
    patients = simulate_patients(kb, 100, seed=0, species_weights={"Species b": 1.0})
    assert {p.species for p in patients} == {"Species b"}
    with pytest.raises(ValueError):
        simulate_patients(kb, 10, seed=0, species_weights={"Unknown": 1.0})


def test_assign_splits() -> None:
    splits = assign_splits(103, SPLITS, seed=0)
    counts = {k: int((splits == k).sum()) for k in SPLITS}
    assert counts == {"train": 63, "calibration": 20, "test": 20}
    assert (splits == assign_splits(103, SPLITS, seed=0)).all()
    with pytest.raises(ValueError):
        assign_splits(10, {"train": 0.5, "test": 0.6}, seed=0)


def test_dataframes(kb: KnowledgeBase) -> None:
    patients = simulate_patients(kb, 20, seed=0)
    df = to_dataframe(patients)
    assert len(df) == 20
    assert {"venom_syndrome", "dry_bite", "hour_of_day", "indoor", "asleep"} <= set(df.columns)
    assert "onset_late" not in df.columns and "onset_never" not in df.columns
    events = events_dataframe(patients)
    assert len(events) == sum(len(p.course) for p in patients)
    assert events["observed"].sum() == sum(len(p.observed_events) for p in patients)
