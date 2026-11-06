"""Tests for knowledge overrides and src/data/sensitivity.py. Fixture data is made up."""

import json
from pathlib import Path

import pytest

from src.data.generate import generate
from src.data.knowledge import apply_overrides, load_knowledge
from src.data.sensitivity import summarise, variant_config


def test_apply_overrides(knowledge_dir: Path) -> None:
    kb = load_knowledge(knowledge_dir)
    changed = apply_overrides(kb, [
        {"table": "species", "match": {"species": "Species a"}, "set": {"dry_bite_rate": 0.9}},
        {"table": "clinical", "match": {"species": "Species a", "symptom": "vomit"}, "set": {"frequency": 0.0}},
    ])
    assert changed.species.set_index("species").loc["Species a", "dry_bite_rate"] == 0.9
    assert kb.species.set_index("species").loc["Species a", "dry_bite_rate"] == 0.0  # original untouched
    clinical = changed.clinical.set_index(["species", "symptom"])
    assert clinical.loc[("Species a", "vomit"), "frequency"] == 0.0


@pytest.mark.parametrize(
    "bad",
    [
        {"table": "clinical", "match": {"species": "Species a", "symptom": "nope"}, "set": {"frequency": 0}},
        {"table": "clinical", "match": {"species": "Species a"}, "set": {"frequency": 0}},
        {"table": "species", "match": {"species": "Species a"}, "set": {"nope": 1}},
        {"table": "symptoms", "match": {"symptom": "neuro"}, "set": {"marker": "none"}},
    ],
)
def test_apply_overrides_rejects_bad(knowledge_dir: Path, bad: dict) -> None:
    with pytest.raises(ValueError):
        apply_overrides(load_knowledge(knowledge_dir), [bad])


def test_variant_config_and_summary(knowledge_dir: Path, tmp_path: Path) -> None:
    base = {"name": "b", "seed": 3, "n_patients": 200, "knowledge_dir": str(knowledge_dir),
            "output_dir": "unused", "severity_correlation": 0.5}
    variant = {"name": "dry", "set": {"severity_correlation": 0.0},
               "knowledge_overrides": [{"table": "species", "match": {"species": "Species a"}, "set": {"dry_bite_rate": 1.0}}]}
    config = variant_config(base, variant, str(tmp_path))
    assert config["severity_correlation"] == 0.0 and base["severity_correlation"] == 0.5
    meta = json.loads((generate(config) / "meta.json").read_text())
    row = summarise(meta, variant)
    assert row["variant"] == "dry" and 0 <= row["critical_error_rate"] <= 1
    assert meta["config"]["knowledge_overrides"][0]["set"]["dry_bite_rate"] == 1.0
