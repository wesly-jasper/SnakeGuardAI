"""Tests for src/data/knowledge.py."""

import warnings
from pathlib import Path

import pytest

from src.data.knowledge import load_knowledge, read_bib_keys, split_keys
from tests.conftest import CLINICAL, CONTEXT, SPECIES, write_knowledge

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_loads_fixture_strictly(knowledge_dir: Path) -> None:
    kb = load_knowledge(knowledge_dir, require_citations=True, require_verified=True)
    assert len(kb.clinical) == len(CLINICAL)
    assert kb.marker_of()["haemo"] == "haemotoxic"


def test_split_keys() -> None:
    assert split_keys("a2020; b2021 ;") == ["a2020", "b2021"]
    assert split_keys("") == []


def test_bib_keys(knowledge_dir: Path) -> None:
    assert read_bib_keys(knowledge_dir / "sources.bib") == {"fake2026", "other2025"}


@pytest.mark.parametrize(
    "bad_row",
    [
        ("Species a", "swell", 0.0, 1.0, 1.5, "fake2026", "", True),  # frequency > 1
        ("Species a", "swell", 5.0, 1.0, 0.5, "fake2026", "", True),  # min > max
        ("Species a", "made_up", 0.0, 1.0, 0.5, "fake2026", "", True),  # unknown symptom
        ("Species z", "swell", 0.0, 1.0, 0.5, "fake2026", "", True),  # unknown species
        ("Species a", "neuro", 0.0, 1.0, 0.5, "fake2026", "", True),  # duplicate row
    ],
)
def test_rejects_bad_clinical_rows(tmp_path: Path, bad_row: tuple) -> None:
    with pytest.raises(ValueError):
        load_knowledge(write_knowledge(tmp_path, clinical=CLINICAL + [bad_row]))


def test_rejects_bad_context_feature(tmp_path: Path) -> None:
    rows = CONTEXT + [("Species a", "rainy", 0.5, "fake2026", "", True)]
    with pytest.raises(ValueError, match="context feature"):
        load_knowledge(write_knowledge(tmp_path, context=rows))


@pytest.mark.parametrize("key", ["TODO", "fake2026; missing1999", ""])
def test_require_citations(tmp_path: Path, key: str) -> None:
    rows = CLINICAL + [("Species a", "swell", 0.0, 1.0, 0.5, key, "", True)]
    root = write_knowledge(tmp_path, clinical=rows)
    assert len(load_knowledge(root).clinical) == len(rows)
    with pytest.raises(ValueError, match="citation"):
        load_knowledge(root, require_citations=True)


def test_require_citations_needs_dry_rate(tmp_path: Path) -> None:
    species = [SPECIES[0][:3] + (None, "fake2026", "", True)] + SPECIES[1:]
    root = write_knowledge(tmp_path, species=species)
    with pytest.warns(UserWarning, match="dry_bite_rate"):
        load_knowledge(root)
    with pytest.raises(ValueError):
        load_knowledge(root, require_citations=True)


def test_require_verified(tmp_path: Path) -> None:
    rows = CLINICAL + [("Species a", "swell", 0.0, 1.0, 0.5, "fake2026", "", False)]
    root = write_knowledge(tmp_path, clinical=rows)
    load_knowledge(root, require_citations=True)
    with pytest.raises(ValueError, match="verified"):
        load_knowledge(root, require_verified=True)


def test_incomplete_rows_skipped(tmp_path: Path) -> None:
    rows = CLINICAL + [("Species a", "swell", None, None, None, "TODO", "", False)]
    with pytest.warns(UserWarning, match="incomplete"):
        kb = load_knowledge(write_knowledge(tmp_path, clinical=rows))
    assert len(kb.clinical) == len(CLINICAL)


def test_zero_frequency_row_needs_no_onset(tmp_path: Path) -> None:
    rows = CLINICAL + [("Species a", "haemo", None, None, 0.0, "fake2026", "", True)]
    kb = load_knowledge(write_knowledge(tmp_path, clinical=rows), require_citations=True)
    assert len(kb.clinical) == len(rows)


def test_real_knowledge_loads() -> None:
    """The committed tables parse; placeholder rows are skipped until filled."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        kb = load_knowledge(REPO_ROOT / "knowledge")
    assert set(kb.clinical["symptom"]) <= set(kb.symptoms["symptom"])
