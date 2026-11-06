"""Tests for src/data/vignettes.py. Fixture data is made up."""

from pathlib import Path

import pandas as pd

from src.data.generate import generate
from src.data.vignettes import build_kit, describe, load_dataset, stratified_sample


def _dataset(knowledge_dir: Path, tmp_path: Path) -> Path:
    return generate({"name": "t", "seed": 2, "n_patients": 300, "knowledge_dir": str(knowledge_dir),
                     "output_dir": str(tmp_path / "ds")})


def test_describe_marks_presentation() -> None:
    patient = pd.Series({"hour_of_day": 2.5, "indoor": True, "asleep": None, "presentation_hours": 3.0})
    events = pd.DataFrame({"patient_id": [0, 0], "symptom": ["ptosis", "vomiting"], "hours": [1.0, 5.0]})
    text = describe(patient, events, {"ptosis": "Drooping eyelids"})
    assert "02:30" in text and "indoors" in text and "not recorded" in text
    lines = text.splitlines()
    assert lines.index("  - 1.0 h: Drooping eyelids") < lines.index("  - --- presentation ---") < lines.index("  - 5.0 h: vomiting")


def test_kit_is_blinded_and_keyed(knowledge_dir: Path, tmp_path: Path) -> None:
    patients, events = load_dataset(_dataset(knowledge_dir, tmp_path))
    sample = stratified_sample(patients, 9, seed=0)
    assert sample["venom_syndrome"].nunique() == patients["venom_syndrome"].nunique()
    real = patients.head(2)
    text, form, key = build_kit([("simulated", sample, events), ("real", real, events)], {}, seed=1)
    assert len(form) == len(key) == len(sample) + 2
    assert set(key["source"]) == {"simulated", "real"}
    for hidden in ["Species a", "neurotoxic", "simulated", "real"]:
        assert hidden not in text.split("Do not look anything up.")[1]
    assert form.drop(columns="vignette").eq("").all().all()
