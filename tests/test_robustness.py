"""Tests for the input-corruption functions and the robustness / ablation CLIs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.features import ModelInputs
from src.data.generate import generate
from src.robustness import (
    drop_events,
    false_reports,
    missing_presentation,
    omit_reported,
    onset_noise,
)
from tests.conftest import write_knowledge

SYMPTOMS = ("local_pain", "ptosis", "bleed")


def inputs() -> ModelInputs:
    rng = np.random.default_rng(0)
    seqs = tuple(np.array([[0, 0.5], [1, 1.0], [2, 2.0]]) if i % 2 else np.array([[1, 0.2]]) for i in range(200))
    context = pd.DataFrame({"hour_of_day": [1.0] * 200, "indoor": [True] * 200, "asleep": [False] * 200})
    return ModelInputs(seqs, rng.uniform(2.5, 5.0, 200), context, SYMPTOMS, {})


def frozen(x: ModelInputs) -> list[np.ndarray]:
    return [s.copy() for s in x.sequences]


@pytest.mark.parametrize("fn", [
    lambda x, lv, rng: drop_events(x, lv, rng),
    lambda x, lv, rng: omit_reported(x, lv, rng, ("local_pain",)),
    lambda x, lv, rng: false_reports(x, lv, rng, (0, 1, 2)),
    lambda x, lv, rng: onset_noise(x, lv, rng),
    lambda x, lv, rng: missing_presentation(x, lv, rng),
])
def test_level_zero_is_identity_and_input_never_mutated(fn) -> None:
    clean = inputs()
    before, pres = frozen(clean), clean.presentation.copy()
    same = fn(clean, 0.0, np.random.default_rng(1))
    for a, b in zip(same.sequences, before):
        np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(same.presentation, pres)
    fn(clean, 0.3, np.random.default_rng(1))
    for a, b in zip(clean.sequences, before):
        np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(clean.presentation, pres)


def test_drop_and_omission_rates() -> None:
    clean = inputs()
    n = clean.n_observed.sum()
    dropped = drop_events(clean, 0.3, np.random.default_rng(2))
    assert 0.2 < 1 - dropped.n_observed.sum() / n < 0.4
    omitted = omit_reported(clean, 1.0, np.random.default_rng(2), ("local_pain",))
    assert not any((s[:, 0] == 0).any() for s in omitted.sequences)
    assert omitted.n_observed.sum() == n - 100  # only local_pain events removed
    with pytest.raises(ValueError):
        omit_reported(clean, 0.1, np.random.default_rng(2), ("not_a_symptom",))


def test_false_reports_add_new_symptoms_before_presentation() -> None:
    clean = inputs()
    noisy = false_reports(clean, 1.0, np.random.default_rng(3), (0, 1, 2))
    for s0, s1, p in zip(clean.sequences, noisy.sequences, clean.presentation):
        if len(s0) < 3:
            assert len(s1) == len(s0) + 1
            assert len(set(s1[:, 0])) == len(s1)  # never duplicates an existing symptom
        assert (s1[:, 1] <= p).all() and (np.diff(s1[:, 1]) >= 0).all()


def test_onset_noise_clipped_and_sorted() -> None:
    clean = inputs()
    noisy = onset_noise(clean, 0.3, np.random.default_rng(4))
    changed = False
    for s0, s1, p in zip(clean.sequences, noisy.sequences, clean.presentation):
        assert ((s1[:, 1] >= 0) & (s1[:, 1] <= p)).all() and (np.diff(s1[:, 1]) >= 0).all()
        assert sorted(s0[:, 0]) == sorted(s1[:, 0])
        changed |= not np.array_equal(s0, s1)
    assert changed


def test_missing_presentation_and_bad_levels() -> None:
    noisy = missing_presentation(inputs(), 0.5, np.random.default_rng(5))
    assert 0.3 < np.isnan(noisy.presentation).mean() < 0.7
    for bad in (-0.1, 1.5):
        with pytest.raises(ValueError):
            drop_events(inputs(), bad, np.random.default_rng(0))


@pytest.fixture(scope="module")
def sim(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("rob")
    return generate({"name": "r", "seed": 4, "n_patients": 500, "knowledge_dir": str(write_knowledge(root / "k")),
                     "output_dir": str(root / "sim"), "presentation_hours": [0.5, 4.0]})


XGB = {"n_estimators": 15, "early_stopping_rounds": 5}


def test_robustness_cli(sim: Path, tmp_path: Path) -> None:
    from src.robustness import run

    before = (sim / "events.csv").read_bytes()
    config = {
        "name": "r", "dataset": str(sim), "output_dir": str(tmp_path / "rob"), "seeds": [0], "torch_threads": 1,
        "levels": [0.0, 0.3], "omission_symptoms": ["vomit"],
        "models": {"rule": {}, "xgboost": {"params": XGB}, "logistic_regression": {},
                   "transformer": {"d_model": 16, "n_heads": 2, "n_layers": 1, "max_epochs": 1}},
    }
    run(config)
    assert (sim / "events.csv").read_bytes() == before  # clean dataset unchanged
    res = json.loads((tmp_path / "rob" / "robustness.json").read_text())
    s = res["xgboost"]["summary"]
    assert set(s) == {"missing_symptom", "omission", "false_report", "onset_noise", "missing_presentation"}
    assert s["missing_presentation"]["0.3"] is not None  # XGBoost handles NaN
    assert res["logistic_regression"]["summary"]["missing_presentation"]["0.3"] is None  # not supported
    assert res["transformer"]["summary"]["missing_presentation"]["0.0"] is not None
    # level 0 equals the clean result for every corruption type
    clean = {k: s[k]["0.0"]["macro_f1"]["mean"] for k in s}
    assert len(set(clean.values())) == 1
    assert "SIMULATION RESULTS" in (tmp_path / "rob" / "report.md").read_text(encoding="utf-8")
    info = json.loads((tmp_path / "rob" / "run.json").read_text())
    assert info["status"] == "complete" and info["splits"]["n_total"] == 500 and info["levels"] == [0.0, 0.3]
    with pytest.raises(FileExistsError):
        run(config)


def test_ablation_cli(sim: Path, tmp_path: Path) -> None:
    from src.ablation import run

    config = {
        "name": "a", "dataset": str(sim), "output_dir": str(tmp_path / "abl"), "seeds": [0],
        "model": {"kind": "xgboost", "heads": ["syndrome"], "params": XGB},
        "experiments": {
            "A_full": {}, "B_presence_only": {"onset": False, "elapsed": False},
            "C_temporal_only": {"symptom_identity": False},
            "D_no_presentation": {"presentation": False, "elapsed": False},
            "F_no_local": {"drop_groups": ["local"]}, "G_no_systemic": {"drop_groups": ["systemic"]},
            "H_context_only": {"symptoms": False, "presentation": False, "context": True},
            "I_symptoms_plus_context": {"context": True},
        },
    }
    run(config)
    out = tmp_path / "abl"
    res = json.loads((out / "ablation.json").read_text())
    loo = [k for k in res if k.startswith("E_drop_")]
    assert loo
    for name in loo:
        dropped = name[len("E_drop_"):]
        # the dropped symptom is never present for anyone in the experiment's inputs
        assert f"present_{dropped}" in res[name]["features"]
    for name in res:
        assert (out / "experiments" / name / "config.json").exists()
        assert (out / "experiments" / name / "metrics.json").exists()
        # same patients and labels in every experiment
        assert np.array(res[name]["runs"][0]["metrics"]["confusion"]).sum(1).tolist() == \
            np.array(res["A_full"]["runs"][0]["metrics"]["confusion"]).sum(1).tolist()
    assert res["H_context_only"]["features"] == ["hour_sin", "hour_cos", "hour_missing", "indoor", "asleep"]
    assert not any(n.startswith("present_") for n in res["C_temporal_only"]["features"])
    assert "presentation_hours" not in res["D_no_presentation"]["features"]
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "not causal clinical evidence" in report and "SIMULATION RESULTS" in report
    info = json.loads((out / "run.json").read_text())
    assert info["status"] == "complete" and info["symptoms_never_observed_in_inputs"] is not None
