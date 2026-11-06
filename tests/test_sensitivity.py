"""Tests for knowledge overrides and src/data/sensitivity.py. Fixture data is made up."""

import json
from pathlib import Path

import pytest

from src.data.generate import generate
from src.data.knowledge import apply_overrides, load_knowledge
from src.data.sensitivity import summarise, t_interval, variant_config


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


def test_multi_seed_run_and_intervals(knowledge_dir: Path, tmp_path: Path) -> None:
    import yaml

    from src.data.sensitivity import aggregate, render, run

    base = {"name": "b", "seed": 3, "n_patients": 200, "knowledge_dir": str(knowledge_dir),
            "output_dir": "unused"}
    (tmp_path / "base.yaml").write_text(yaml.safe_dump(base))
    sens = {
        "base_config": str(tmp_path / "base.yaml"), "output_dir": str(tmp_path / "sens"), "seeds": [1, 2, 3],
        "variants": [
            {"name": "base"},
            {"name": "fb", "basis": "assumption",
             "set": {"onset_fallback": {"hours": [0, 24], "source_key": "fake2026"}}},
        ],
    }
    per_seed = run(sens)
    assert len(per_seed) == 6 and set(per_seed["seed"]) == {1, 2, 3}
    meta = json.loads((tmp_path / "sens" / "fb" / "seed_1" / "meta.json").read_text())
    assert meta["experiment_type"] == "sensitivity"  # fallback only inside labelled runs
    assert (tmp_path / "sens" / "base" / "seed_1" / "patients.csv").exists()
    assert not (tmp_path / "sens" / "base" / "seed_2" / "patients.csv").exists()
    summary = aggregate(per_seed)
    row = summary.set_index("variant").loc["base"]
    assert row["n_seeds"] == 3
    assert row["critical_error_rate_ci_low"] <= row["critical_error_rate"] <= row["critical_error_rate_ci_high"]
    assert "assumption" in render(summary, sens)
    with pytest.raises(ValueError, match="basis"):
        run({**sens, "variants": [{"name": "x", "basis": "guess"}]})


def test_t_interval() -> None:
    import pandas as pd

    mean, lo, hi = t_interval(pd.Series([1.0, 2.0, 3.0]))
    assert mean == 2.0 and lo == pytest.approx(2 - 4.303 / 3 ** 0.5, abs=1e-3) and hi > 3
    mean, lo, hi = t_interval(pd.Series([5.0]))
    assert mean == 5.0 and pd.isna(lo)
