"""Tests for src/data/report.py and src/data/checklist.py. Fixture data is made up."""

from pathlib import Path

import pytest

from src.data.checklist import render, unverified_rows
from src.data.knowledge import load_knowledge
from src.data.report import build_report, critical_error_rate, frequency_check, rule_predictions
from src.data.simulator import DRY_LABEL, simulate_patients
from tests.conftest import CLINICAL, write_knowledge


def test_critical_error_rate() -> None:
    true = ["neurotoxic", "haemotoxic", DRY_LABEL, "local-only"]
    pred = [DRY_LABEL, "haemotoxic", DRY_LABEL, DRY_LABEL]
    assert critical_error_rate(true, pred) == pytest.approx(2 / 3)


def test_rule_predictions_use_observed_events_only(knowledge_dir: Path) -> None:
    kb = load_knowledge(knowledge_dir)
    patients = simulate_patients(kb, 300, seed=0)
    preds = rule_predictions(patients, kb.marker_of())
    for p, pred in zip(patients, preds):
        if not p.observed_events:
            assert pred == DRY_LABEL
        if p.species == "Species c" and p.observed_events:
            assert pred == "local-only"  # rule does not know the species is harmless


def test_frequency_check_matches_table(knowledge_dir: Path) -> None:
    kb = load_knowledge(knowledge_dir)
    freq = frequency_check(simulate_patients(kb, 3000, seed=0), kb)
    assert (abs(freq["simulated_rate"] - freq["table_frequency"]) < 0.05).all()


def test_build_report(knowledge_dir: Path) -> None:
    kb = load_knowledge(knowledge_dir)
    patients = simulate_patients(kb, 100, seed=0)
    text = build_report(patients, ["test"] * 100, kb, notes=["note one"])
    assert "SIMULATION RESULTS" in text and "note one" in text and "critical_error_rate" in text


def test_checklist_lists_only_unverified(tmp_path: Path) -> None:
    rows = CLINICAL + [("Species a", "swell", None, None, 0.3, "fake2026", "quote", False)]
    root = write_knowledge(tmp_path, clinical=rows)
    unverified = unverified_rows(root)
    assert unverified["item"].tolist() == ["Species a / swell"]
    assert "- [ ]" in render(unverified)
