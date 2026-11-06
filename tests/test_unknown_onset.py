"""Regression tests for unknown-onset handling (exclude / label_only / fallback).

Fixture tables are made up; not clinical data.
"""

import json
import math
from pathlib import Path

import pandas as pd
import pytest
from scipy import stats

from src.data.generate import generate
from src.data.knowledge import ORDER_COLUMNS, load_knowledge
from src.data.simulator import DRY_LABEL, build_specs, fill_onsets, simulate_patients
from tests.conftest import CLINICAL, write_knowledge

# Species b: haemo has a cited window; "neuro" is present in every course but its onset is unknown.
ROWS = [r for r in CLINICAL if r[0] != "Species b"] + [
    ("Species b", "haemo", 0.5, 3.0, 0.4, "fake2026", "", True),
    ("Species b", "neuro", None, None, 1.0, "fake2026", "", True),
]


@pytest.fixture
def kb(tmp_path: Path):
    return load_knowledge(write_knowledge(tmp_path, clinical=ROWS), allow_missing_onset=True)


def _b(kb, **kwargs):
    return [p for p in simulate_patients(kb, 2000, seed=0, species_weights={"Species b": 1.0}, **kwargs)]


def test_fill_onsets_modes(kb) -> None:
    clinical = kb.clinical[kb.clinical["species"] == "Species b"]
    excluded = fill_onsets(clinical, None, "exclude")
    assert list(excluded["symptom"]) == ["haemo"]
    label_only = fill_onsets(clinical, None, "label_only").set_index("symptom")
    assert label_only.loc["neuro", "onset_unknown"] and not label_only.loc["haemo", "onset_unknown"]
    assert math.isnan(label_only.loc["neuro", "onset_min_hours"])
    filled = fill_onsets(clinical, (1.0, 5.0)).set_index("symptom")
    assert filled.loc["neuro", "onset_assumed"] and not filled["onset_unknown"].any()
    with pytest.raises(ValueError, match="unknown_onset"):
        fill_onsets(clinical, None, "guess")


def test_label_only_counts_for_label_but_is_never_observed(kb) -> None:
    patients = _b(kb, unknown_onset="label_only")
    for p in patients:
        neuro = [e for e in p.course if e.symptom == "neuro"]
        assert len(neuro) == 1 and neuro[0].onset_unknown and math.isnan(neuro[0].hours)
        assert p.venom_syndrome in {"neurotoxic", "haemotoxic"}  # never mislabelled dry
        assert "neuro" not in {e.symptom for e in p.observed_events}
        assert p.course[-1].onset_unknown  # unknown-onset events sort last


def test_exclude_mislabels_where_label_only_does_not(kb) -> None:
    excluded = _b(kb, unknown_onset="exclude")
    label_only = _b(kb, unknown_onset="label_only")
    assert sum(p.venom_syndrome == DRY_LABEL for p in excluded) > 1000  # haemo in only 40%
    assert sum(p.venom_syndrome == DRY_LABEL for p in label_only) == 0


def test_label_only_keeps_frequency_and_timed_marginals(kb) -> None:
    patients = _b(kb, unknown_onset="label_only", severity_correlation=0.5)
    has_haemo = [any(e.symptom == "haemo" for e in p.course) for p in patients]
    assert stats.binomtest(sum(has_haemo), len(has_haemo), 0.4).pvalue > 0.01
    hours = [e.hours for p in patients for e in p.course if e.symptom == "haemo"]
    assert all(0.5 <= h <= 3.0 for h in hours)


def test_order_rules_with_unknown_onset_are_not_enforced(tmp_path: Path) -> None:
    root = write_knowledge(tmp_path, clinical=ROWS)
    pd.DataFrame([("*", "neuro", "haemo", "fake2026", "", True)], columns=ORDER_COLUMNS).to_csv(
        root / "onset_order.csv", index=False)
    kb = load_knowledge(root, allow_missing_onset=True)
    spec = build_specs(kb, None, "label_only")["Species b"]
    assert spec.order == ()
    assert all(p.order_violations == 0 for p in _b(kb, unknown_onset="label_only"))


def test_generate_label_only_meta_and_events(tmp_path: Path) -> None:
    root = write_knowledge(tmp_path / "k", clinical=ROWS)
    base = {"name": "t", "seed": 1, "n_patients": 300, "knowledge_dir": str(root)}
    out = generate({**base, "output_dir": str(tmp_path / "lo"), "unknown_onset": "label_only"})
    meta = json.loads((out / "meta.json").read_text())
    assert meta["experiment_type"] == "primary" and meta["unknown_onset"] == "label_only"
    assert meta["n_clinical_rows_label_only"] == 1 and meta["n_clinical_rows_excluded_unknown_onset"] == 0
    assert meta["n_events_with_unknown_onset"] > 0
    assert any("never part of the model input" in a for a in meta["assumptions"])
    events = pd.read_csv(out / "events.csv")
    unknown = events[events["onset_unknown"]]
    assert unknown["hours"].isna().all() and not unknown["observed"].any()
    assert "label-only" in (out / "report.md").read_text()
    assert "unknown (label only)" in (out / "onset_diagnostics.md").read_text()


def test_generate_unknown_onset_mode_checked(tmp_path: Path) -> None:
    root = write_knowledge(tmp_path / "k", clinical=ROWS)
    base = {"name": "t", "seed": 1, "n_patients": 10, "knowledge_dir": str(root), "output_dir": str(tmp_path / "o")}
    with pytest.raises(ValueError, match="unknown_onset must be"):
        generate({**base, "unknown_onset": "guess"})
    with pytest.raises(ValueError, match="needs onset_fallback"):
        generate({**base, "unknown_onset": "fallback", "experiment_type": "sensitivity"})
    fb = {"onset_fallback": {"hours": [0, 24], "source_key": "fake2026"}, "experiment_type": "sensitivity"}
    with pytest.raises(ValueError, match="needs unknown_onset: fallback"):
        generate({**base, **fb, "unknown_onset": "label_only"})
    meta = json.loads((generate({**base, **fb}) / "meta.json").read_text())
    assert meta["unknown_onset"] == "fallback" and meta["n_clinical_rows_using_onset_fallback"] == 1
