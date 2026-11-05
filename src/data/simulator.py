"""Synthetic snakebite patient simulator.

Samples patients from the literature-derived clinical knowledge table
(knowledge/clinical_table.csv). Everything produced here is SIMULATED data and any
result computed from it must be labelled as a simulation result.

Placeholders until later phases:
- GPS is uniform over India's bounding box and month is uniform. The real
  P(species | location, month) prior comes from GBIF occurrences in Phase 3.
- Time to presentation is uniform over `presentation_hours_range`.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS: list[str] = [
    "species",
    "venom_syndrome",
    "symptom",
    "onset_min_hours",
    "onset_max_hours",
    "frequency",
    "source_key",
]
NUMERIC_COLUMNS: list[str] = ["onset_min_hours", "onset_max_hours", "frequency"]
VENOM_SYNDROMES: frozenset[str] = frozenset(
    {"neurotoxic", "haemotoxic", "local-only", "non-venomous"}
)
PLACEHOLDER_SOURCE = "TODO"

# Rough bounding box of India (lat, lon). Placeholder until the Phase 3 geo prior.
INDIA_LAT_RANGE: tuple[float, float] = (6.5, 35.5)
INDIA_LON_RANGE: tuple[float, float] = (68.0, 97.5)


@dataclass(frozen=True)
class SymptomEvent:
    symptom: str
    hours: float


@dataclass(frozen=True)
class SyntheticPatient:
    species: str
    venom_syndrome: str
    events: tuple[SymptomEvent, ...]
    lat: float
    lon: float
    month: int
    presentation_hours: float


def read_bib_keys(bib_path: str | Path) -> set[str]:
    """Return the citation keys defined in a BibTeX file."""
    text = Path(bib_path).read_text(encoding="utf-8")
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))


def load_clinical_table(
    path: str | Path,
    bib_path: str | Path | None = None,
    require_citations: bool = False,
) -> pd.DataFrame:
    """Load and validate the clinical knowledge table.

    Rows with blank numeric cells are skipped with a warning. With
    `require_citations=True`, every row must be complete and its `source_key` must
    exist in `bib_path` (default: sources.bib next to the table).
    """
    path = Path(path)
    table = pd.read_csv(path, dtype={"source_key": "string"})
    missing = [c for c in COLUMNS if c not in table.columns]
    if missing:
        raise ValueError(f"clinical table missing columns: {missing}")
    table = table[COLUMNS].copy()
    table["source_key"] = table["source_key"].fillna("").str.strip()

    if require_citations:
        bib_keys = read_bib_keys(bib_path or path.with_name("sources.bib"))
        uncited = table[~table["source_key"].isin(bib_keys)]
        if not uncited.empty:
            raise ValueError(
                f"{len(uncited)} row(s) lack a citation in sources.bib: "
                f"{uncited['source_key'].tolist()}"
            )

    incomplete = table[NUMERIC_COLUMNS].isna().any(axis=1)
    if incomplete.any():
        if require_citations:
            raise ValueError(f"{int(incomplete.sum())} row(s) have blank numeric cells")
        warnings.warn(
            f"skipping {int(incomplete.sum())} incomplete row(s) in {path.name}",
            stacklevel=2,
        )
        table = table[~incomplete].reset_index(drop=True)

    _validate_rows(table)
    return table


def _validate_rows(table: pd.DataFrame) -> None:
    bad_syndrome = ~table["venom_syndrome"].isin(VENOM_SYNDROMES)
    if bad_syndrome.any():
        raise ValueError(
            f"unknown venom_syndrome: {table.loc[bad_syndrome, 'venom_syndrome'].unique().tolist()}"
        )
    if ((table["frequency"] < 0) | (table["frequency"] > 1)).any():
        raise ValueError("frequency must be within [0, 1]")
    if (table["onset_min_hours"] < 0).any():
        raise ValueError("onset_min_hours must be >= 0")
    if (table["onset_min_hours"] > table["onset_max_hours"]).any():
        raise ValueError("onset_min_hours must be <= onset_max_hours")
    syndromes_per_species = table.groupby("species")["venom_syndrome"].nunique()
    if (syndromes_per_species > 1).any():
        raise ValueError(
            "each species must have one venom_syndrome: "
            f"{syndromes_per_species[syndromes_per_species > 1].index.tolist()}"
        )


def simulate_patient(
    rows: pd.DataFrame,
    rng: np.random.Generator,
    presentation_hours_range: tuple[float, float] = (0.5, 24.0),
) -> SyntheticPatient:
    """Sample one patient from the table rows of a single species."""
    presentation = float(rng.uniform(*presentation_hours_range))
    present = rng.random(len(rows)) < rows["frequency"].to_numpy()
    onsets = rng.uniform(rows["onset_min_hours"].to_numpy(), rows["onset_max_hours"].to_numpy())
    events = sorted(
        (
            SymptomEvent(symptom, float(hours))
            for symptom, hours, keep in zip(rows["symptom"], onsets, present)
            if keep and hours <= presentation
        ),
        key=lambda e: e.hours,
    )
    return SyntheticPatient(
        species=str(rows["species"].iloc[0]),
        venom_syndrome=str(rows["venom_syndrome"].iloc[0]),
        events=tuple(events),
        lat=float(rng.uniform(*INDIA_LAT_RANGE)),
        lon=float(rng.uniform(*INDIA_LON_RANGE)),
        month=int(rng.integers(1, 13)),
        presentation_hours=presentation,
    )


def simulate_patients(
    table: pd.DataFrame,
    n: int,
    seed: int,
    species_weights: dict[str, float] | None = None,
    presentation_hours_range: tuple[float, float] = (0.5, 24.0),
) -> list[SyntheticPatient]:
    """Sample `n` synthetic patients. Species are uniform unless weights are given."""
    if table.empty:
        warnings.warn("clinical table has no usable rows; returning no patients", stacklevel=2)
        return []
    rng = np.random.default_rng(seed)
    by_species = {name: rows for name, rows in table.groupby("species", sort=True)}
    species = list(by_species)
    if species_weights is None:
        probs = np.full(len(species), 1.0 / len(species))
    else:
        unknown = set(species_weights) - set(species)
        if unknown:
            raise ValueError(f"weights given for species not in table: {sorted(unknown)}")
        probs = np.array([species_weights.get(s, 0.0) for s in species], dtype=float)
        if probs.sum() <= 0:
            raise ValueError("species_weights must have a positive sum")
        probs /= probs.sum()
    picks = rng.choice(len(species), size=n, p=probs)
    return [
        simulate_patient(by_species[species[i]], rng, presentation_hours_range) for i in picks
    ]


def to_dataframe(patients: list[SyntheticPatient]) -> pd.DataFrame:
    """Flatten patients to one row each, with `onset_<symptom>` columns (NaN if absent)."""
    records = []
    for pid, p in enumerate(patients):
        record: dict[str, object] = {
            "patient_id": pid,
            "species": p.species,
            "venom_syndrome": p.venom_syndrome,
            "lat": p.lat,
            "lon": p.lon,
            "month": p.month,
            "presentation_hours": p.presentation_hours,
        }
        record.update({f"onset_{e.symptom}": e.hours for e in p.events})
        records.append(record)
    return pd.DataFrame.from_records(records)
