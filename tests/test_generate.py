"""Tests for src/data/generate.py."""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.data.generate import generate


def test_generate_writes_reproducible_dataset(knowledge_dir: Path, tmp_path: Path) -> None:
    config = {
        "name": "t",
        "seed": 7,
        "n_patients": 100,
        "knowledge_dir": str(knowledge_dir),
        "output_dir": str(tmp_path / "out"),
        "require_citations": True,
    }
    out = generate(config)
    first = (out / "patients.csv").read_text()
    patients = pd.read_csv(out / "patients.csv")
    meta = json.loads((out / "meta.json").read_text())
    assert len(patients) == 100
    assert set(patients["split"]) == {"train", "calibration", "test"}
    assert meta["SIMULATED"] is True
    assert meta["config"]["seed"] == 7
    assert "clinical_table.csv" in meta["knowledge_hashes"]
    assert (out / "events.csv").exists()
    assert "SIMULATION RESULTS" in (out / "report.md").read_text()
    generate(config)
    assert (out / "patients.csv").read_text() == first


def test_generate_onset_fallback_needs_citation(knowledge_dir: Path, tmp_path: Path) -> None:
    config = {
        "name": "t", "seed": 1, "n_patients": 10,
        "knowledge_dir": str(knowledge_dir), "output_dir": str(tmp_path / "out"),
        "experiment_type": "sensitivity",  # the fallback is an assumption (Phase 1.4)
    }
    meta = json.loads((generate({**config, "onset_fallback": {"hours": [0, 24], "source_key": "fake2026"}}) / "meta.json").read_text())
    assert meta["n_clinical_rows_using_onset_fallback"] == 0
    with pytest.raises(ValueError, match="source_key"):
        generate({**config, "onset_fallback": {"hours": [0, 24], "source_key": "missing"}})


def test_fallback_refused_in_primary_experiment(knowledge_dir: Path, tmp_path: Path) -> None:
    config = {
        "name": "t", "seed": 1, "n_patients": 10, "knowledge_dir": str(knowledge_dir),
        "output_dir": str(tmp_path / "out"), "onset_fallback": {"hours": [0, 24], "source_key": "fake2026"},
    }
    with pytest.raises(ValueError, match="experiment_type: sensitivity"):
        generate(config)
    with pytest.raises(ValueError, match="experiment_type"):
        generate({**config, "experiment_type": "exploratory"})


def test_meta_records_verification_and_assumptions(knowledge_dir: Path, tmp_path: Path) -> None:
    out = generate({"name": "t", "seed": 1, "n_patients": 50, "knowledge_dir": str(knowledge_dir),
                    "output_dir": str(tmp_path / "out")})
    meta = json.loads((out / "meta.json").read_text())
    assert meta["experiment_type"] == "primary"
    assert set(meta["verification"]) == {"species.csv", "clinical_table.csv", "context_table.csv"}
    assert meta["n_rows_unverified"] == sum(v["unverified"] for v in meta["verification"].values())
    assert any("unknown onset are excluded" in a for a in meta["assumptions"])
    assert meta["git_commit"]
    assert (out / "onset_diagnostics.md").exists()
    assert meta["n_envenomed_without_any_symptom"] >= 0
    assert "label artefact" in (out / "report.md").read_text()
    events = pd.read_csv(out / "events.csv")
    assert not events["onset_assumed"].any()


def test_generate_rejects_bad_counts(knowledge_dir: Path, tmp_path: Path) -> None:
    base = {"name": "t", "seed": 1, "knowledge_dir": str(knowledge_dir), "output_dir": str(tmp_path / "o")}
    for bad in (-1, 2.5, True, "10"):
        with pytest.raises(ValueError, match="n_patients"):
            generate({**base, "n_patients": bad})
