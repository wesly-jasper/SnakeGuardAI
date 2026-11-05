"""Shared fixtures. Fixture tables are made up; not clinical data."""

from pathlib import Path

import pandas as pd
import pytest

from src.data.knowledge import (
    CLINICAL_COLUMNS,
    CONTEXT_COLUMNS,
    SPECIES_COLUMNS,
    SYMPTOM_COLUMNS,
)

SYMPTOMS = [
    ("neuro", "neurotoxic", ""),
    ("haemo", "haemotoxic", ""),
    ("swell", "local", ""),
    ("vomit", "none", ""),
    ("never", "local", ""),
    ("late", "local", ""),
]
SPECIES = [
    # species, common_name, group, dry_bite_rate, source_key, evidence, verified
    ("Species a", "A", "venomous", 0.0, "fake2026", "", True),
    ("Species b", "B", "venomous", 0.0, "fake2026", "", True),
    ("Species c", "C", "non-venomous", None, "", "", True),
]
CLINICAL = [
    # species, symptom, onset_min, onset_max, frequency, source_key, evidence, verified
    ("Species a", "neuro", 0.0, 1.0, 1.0, "fake2026", "", True),
    ("Species a", "never", 0.0, 1.0, 0.0, "fake2026", "", True),
    ("Species a", "vomit", 2.0, 6.0, 0.5, "fake2026; other2025", "", True),
    ("Species b", "haemo", 0.5, 3.0, 1.0, "fake2026", "", True),
    ("Species b", "neuro", 0.5, 3.0, 1.0, "fake2026", "", True),
    ("Species b", "late", 100.0, 200.0, 1.0, "fake2026", "", True),
    ("Species c", "swell", 0.0, 1.0, 1.0, "fake2026", "", True),
]
CONTEXT = [
    ("Species a", "night", 1.0, "fake2026", "", True),
    ("Species a", "asleep", 0.5, "fake2026", "", True),
    ("Species b", "night", 0.0, "fake2026", "", True),
]
BIB = "@article{fake2026, title={x}}\n@book{other2025,\n title={y}}\n"


def write_knowledge(
    root: Path,
    symptoms: list[tuple] = SYMPTOMS,
    species: list[tuple] = SPECIES,
    clinical: list[tuple] = CLINICAL,
    context: list[tuple] = CONTEXT,
    bib: str = BIB,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(symptoms, columns=SYMPTOM_COLUMNS).to_csv(root / "symptoms.csv", index=False)
    pd.DataFrame(species, columns=SPECIES_COLUMNS).to_csv(root / "species.csv", index=False)
    pd.DataFrame(clinical, columns=CLINICAL_COLUMNS).to_csv(root / "clinical_table.csv", index=False)
    pd.DataFrame(context, columns=CONTEXT_COLUMNS).to_csv(root / "context_table.csv", index=False)
    (root / "sources.bib").write_text(bib, encoding="utf-8")
    return root


@pytest.fixture
def knowledge_dir(tmp_path: Path) -> Path:
    return write_knowledge(tmp_path / "knowledge")
