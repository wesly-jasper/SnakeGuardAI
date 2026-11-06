"""Tests for the explainability outputs (src/explain.py)."""

import json
from pathlib import Path

import numpy as np
import pytest

from src.data.features import allowed_feature_names
from src.data.generate import generate
from src.explain import feature_group, groups_of, run
from tests.conftest import write_knowledge


def test_every_allowed_feature_has_a_group() -> None:
    names = ["present_a", "onset_a", "since_a", "presentation_hours", "n_observed", "hour_sin", "asleep"]
    assert [feature_group(n) for n in names] == [
        "symptom_identity", "timing", "timing", "presentation_delay", "symptom_count", "context", "context"]
    with pytest.raises(ValueError):
        feature_group("venom_syndrome")
    by_symptom = groups_of(names, "symptom")
    assert by_symptom["a"] == [0, 1, 2] and by_symptom["context"] == [5, 6]


def test_allowlisted_names_all_grouped() -> None:
    for name in allowed_feature_names(("x", "y")):
        feature_group(name)


@pytest.fixture(scope="module")
def sim(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("ex")
    return generate({"name": "e", "seed": 2, "n_patients": 600, "knowledge_dir": str(write_knowledge(root / "k")),
                     "output_dir": str(root / "sim"), "presentation_hours": [0.5, 4.0]})


def test_explain_end_to_end(sim: Path, tmp_path: Path) -> None:
    config = {"name": "ex", "dataset": str(sim), "output_dir": str(tmp_path / "out"), "model_seed": 0, "n_repeats": 2,
              "models": {"xgboost": {"params": {"n_estimators": 20, "early_stopping_rounds": 5}},
                         "random_forest": {"params": {"n_estimators": 20, "n_jobs": 1}},
                         "xgboost_context": {"params": {"n_estimators": 20, "early_stopping_rounds": 5}}}}
    out = run(config)
    res = json.loads((out / "explanations.json").read_text())
    for name in config["models"]:
        r = res[name]
        assert r["additivity_max_error"] < 1e-3  # contributions add up to the model output
        assert set(r["permutation_block"]) <= {"symptom_identity", "timing", "presentation_delay", "symptom_count",
                                              "context"}
        assert r["examples"] and all(e["top"] is not None for e in r["examples"])
        saved = np.load(out / f"contributions_{name}.npz")
        assert saved["contributions"].shape == (r["n_test"], 4, len(r["features"]))
        assert (out / f"global_feature_{name}.csv").exists()
    assert "context" in res["xgboost_context"]["permutation_block"]
    assert "context" not in res["xgboost"]["permutation_block"]
    assert "Shapley" in res["random_forest"]["method"]  # labelled as NOT Shapley values
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "not causal" in report and "SIMULATION RESULTS" in report
    assert json.loads((out / "run.json").read_text())["status"] == "complete"
    with pytest.raises(ValueError):
        run({**config, "output_dir": str(tmp_path / "o2"), "models": {"transformer": {}}})
