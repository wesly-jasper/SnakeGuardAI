"""Tests for src/data/simulator.py. Fixture tables are made up; not clinical data."""

import warnings
from pathlib import Path

import pandas as pd
import pytest

from src.data.simulator import (
    INDIA_LAT_RANGE,
    INDIA_LON_RANGE,
    COLUMNS,
    load_clinical_table,
    read_bib_keys,
    simulate_patients,
    to_dataframe,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

FIXTURE_ROWS = [
    # species, syndrome, symptom, onset_min, onset_max, frequency, source_key
    ("Species a", "neurotoxic", "always", 0.0, 1.0, 1.0, "fake2026"),
    ("Species a", "neurotoxic", "never", 0.0, 1.0, 0.0, "fake2026"),
    ("Species a", "neurotoxic", "sometimes", 2.0, 6.0, 0.5, "fake2026"),
    ("Species b", "haemotoxic", "always", 0.5, 3.0, 1.0, "fake2026"),
    ("Species b", "haemotoxic", "late", 100.0, 200.0, 1.0, "fake2026"),
]


def write_table(tmp_path: Path, rows: list[tuple], bib: str = "@article{fake2026, title={x}}\n") -> Path:
    csv = tmp_path / "clinical_table.csv"
    pd.DataFrame(rows, columns=COLUMNS).to_csv(csv, index=False)
    (tmp_path / "sources.bib").write_text(bib, encoding="utf-8")
    return csv


@pytest.fixture
def table(tmp_path: Path) -> pd.DataFrame:
    return load_clinical_table(write_table(tmp_path, FIXTURE_ROWS), require_citations=True)


def test_same_seed_is_reproducible(table: pd.DataFrame) -> None:
    assert simulate_patients(table, 50, seed=1) == simulate_patients(table, 50, seed=1)
    assert simulate_patients(table, 50, seed=1) != simulate_patients(table, 50, seed=2)


def test_events_respect_onset_windows_and_presentation(table: pd.DataFrame) -> None:
    windows = {
        (r.species, r.symptom): (r.onset_min_hours, r.onset_max_hours)
        for r in table.itertuples()
    }
    for p in simulate_patients(table, 500, seed=0):
        hours = [e.hours for e in p.events]
        assert hours == sorted(hours)
        for e in p.events:
            lo, hi = windows[(p.species, e.symptom)]
            assert lo <= e.hours <= hi
            assert e.hours <= p.presentation_hours


def test_frequency_extremes(table: pd.DataFrame) -> None:
    patients = simulate_patients(table, 500, seed=0)
    for p in patients:
        symptoms = {e.symptom for e in p.events}
        assert "never" not in symptoms
        # "late" starts after the latest possible presentation (24 h), so never observed.
        assert "late" not in symptoms
        if p.species == "Species a" and p.presentation_hours >= 1.0:
            assert "always" in symptoms
    rate = sum(
        "sometimes" in {e.symptom for e in p.events}
        for p in patients
        if p.species == "Species a" and p.presentation_hours >= 6.0
    ) / sum(1 for p in patients if p.species == "Species a" and p.presentation_hours >= 6.0)
    assert 0.35 < rate < 0.65


def test_context_in_range(table: pd.DataFrame) -> None:
    for p in simulate_patients(table, 300, seed=3):
        assert INDIA_LAT_RANGE[0] <= p.lat <= INDIA_LAT_RANGE[1]
        assert INDIA_LON_RANGE[0] <= p.lon <= INDIA_LON_RANGE[1]
        assert 1 <= p.month <= 12
        assert p.venom_syndrome == {"Species a": "neurotoxic", "Species b": "haemotoxic"}[p.species]


def test_species_weights(table: pd.DataFrame) -> None:
    patients = simulate_patients(table, 100, seed=0, species_weights={"Species b": 1.0})
    assert {p.species for p in patients} == {"Species b"}
    with pytest.raises(ValueError):
        simulate_patients(table, 10, seed=0, species_weights={"Unknown": 1.0})


def test_to_dataframe(table: pd.DataFrame) -> None:
    patients = simulate_patients(table, 20, seed=0)
    df = to_dataframe(patients)
    assert len(df) == 20
    assert {"species", "venom_syndrome", "lat", "lon", "month", "presentation_hours"} <= set(df.columns)
    assert "onset_never" not in df.columns


@pytest.mark.parametrize(
    "bad_row",
    [
        ("Species a", "neurotoxic", "x", 0.0, 1.0, 1.5, "fake2026"),  # frequency > 1
        ("Species a", "neurotoxic", "x", 5.0, 1.0, 0.5, "fake2026"),  # min > max
        ("Species a", "made-up", "x", 0.0, 1.0, 0.5, "fake2026"),  # unknown syndrome
        ("Species a", "haemotoxic", "x", 0.0, 1.0, 0.5, "fake2026"),  # conflicting syndrome
    ],
)
def test_loader_rejects_bad_rows(tmp_path: Path, bad_row: tuple) -> None:
    with pytest.raises(ValueError):
        load_clinical_table(write_table(tmp_path, FIXTURE_ROWS[:1] + [bad_row]))


def test_require_citations(tmp_path: Path) -> None:
    rows = FIXTURE_ROWS[:1] + [("Species a", "neurotoxic", "y", 0.0, 1.0, 0.5, "TODO")]
    path = write_table(tmp_path, rows)
    assert len(load_clinical_table(path)) == 2
    with pytest.raises(ValueError, match="citation"):
        load_clinical_table(path, require_citations=True)


def test_incomplete_rows_skipped(tmp_path: Path) -> None:
    rows = FIXTURE_ROWS[:1] + [("Species a", "neurotoxic", "y", None, None, None, "TODO")]
    with pytest.warns(UserWarning, match="incomplete"):
        loaded = load_clinical_table(write_table(tmp_path, rows))
    assert loaded["symptom"].tolist() == ["always"]


def test_real_table_loads() -> None:
    """The committed table parses; placeholder TODO rows are skipped until filled."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        loaded = load_clinical_table(REPO_ROOT / "knowledge" / "clinical_table.csv")
    assert list(loaded.columns) == COLUMNS
    read_bib_keys(REPO_ROOT / "knowledge" / "sources.bib")
