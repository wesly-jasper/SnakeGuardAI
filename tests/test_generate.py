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
    }
    meta = json.loads((generate({**config, "onset_fallback": {"hours": [0, 24], "source_key": "fake2026"}}) / "meta.json").read_text())
    assert meta["n_clinical_rows_using_onset_fallback"] == 0
    with pytest.raises(ValueError, match="source_key"):
        generate({**config, "onset_fallback": {"hours": [0, 24], "source_key": "missing"}})
