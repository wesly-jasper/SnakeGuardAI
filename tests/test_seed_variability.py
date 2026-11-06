"""Tests for the simulator-seed variability experiment (src/seed_variability.py)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src.seed_variability import bootstrap_sd, dataset_config, decompose, run


def test_dataset_config_changes_only_seed_and_paths() -> None:
    base = {"name": "b", "seed": 42, "n_patients": 100, "output_dir": "x", "severity_correlation": 0.5}
    cfg = dataset_config(base, 7, Path("d"), None)
    assert cfg["seed"] == 7 and cfg["n_patients"] == 100 and cfg["severity_correlation"] == 0.5
    assert Path(cfg["output_dir"]) == Path("d") / "sim_seed_7"
    assert base["seed"] == 42  # base untouched


def test_decompose_separates_model_and_simulator_variation() -> None:
    # dataset effect: +0.1 per simulator seed; model-seed effect: +/-0.01
    rows = [{"sim_seed": s, "model": "m", "model_seed": k, "macro_f1": 0.5 + 0.1 * i + (0.01 if k else -0.01)}
            for i, s in enumerate([1, 2, 3]) for k in (0, 1)]
    per_run = pd.DataFrame(rows)
    for col in ("critical_error_rate", "accuracy", "envenomation_sensitivity", "envenomation_specificity",
                "nll", "ece", "brier"):
        per_run[col] = 0.0
    m = decompose(per_run)["m"]["macro_f1"]
    assert m["model_seed_sd"] == pytest.approx(0.01)
    assert m["sim_seed_sd"] == pytest.approx(0.1)
    assert (m["sim_seed_min"], m["sim_seed_max"]) == pytest.approx((0.5, 0.7))
    assert m["per_sim_seed"] == pytest.approx({1: 0.5, 2: 0.6, 3: 0.7})


def test_bootstrap_sd_zero_for_perfect_and_positive_otherwise() -> None:
    y = np.repeat(np.arange(4), 25)
    assert bootstrap_sd(y, y, None, 50, 0)["macro_f1"] == 0.0
    noisy = np.random.default_rng(0).permutation(y)
    assert bootstrap_sd(y, noisy, None, 50, 0)["macro_f1"] > 0


def test_seed_variability_end_to_end(knowledge_dir: Path, tmp_path: Path) -> None:
    base = {"name": "b", "seed": 1, "n_patients": 300, "knowledge_dir": str(knowledge_dir),
            "output_dir": "unused", "presentation_hours": [0.5, 4.0]}
    (tmp_path / "base.yaml").write_text(yaml.safe_dump(base))
    config = {
        "name": "sv", "base_config": str(tmp_path / "base.yaml"), "simulator_seeds": [1, 2],
        "model_seeds": [0, 1], "data_dir": str(tmp_path / "data"), "output_dir": str(tmp_path / "out"),
        "torch_threads": 1, "bootstrap": 20,
        "models": {"rule": {}, "xgboost": {"params": {"n_estimators": 10, "early_stopping_rounds": 3}}},
    }
    out = run(config)
    res = json.loads((out / "seed_variability.json").read_text())
    assert res["xgboost"]["n_sim_seeds"] == 2 and res["xgboost"]["n_model_seeds"] == 2
    assert res["rule"]["n_model_seeds"] == 1
    per_run = pd.read_csv(out / "per_run.csv")
    assert set(per_run["sim_seed"]) == {1, 2}
    info = json.loads((out / "run.json").read_text())
    assert info["status"] == "complete"
    h1, h2 = (info["datasets"][str(s)]["hashes"]["patients.csv"] for s in (1, 2))
    assert h1 != h2  # independent simulated populations
    for s in (1, 2):  # full training artifacts per simulator seed, recording that seed
        sub = json.loads((out / f"sim_seed_{s}" / "run.json").read_text())
        assert sub["simulator_seed"] == s and sub["model_seeds"] == [0, 1]
    assert "SIMULATION RESULTS" in (out / "report.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        run({**config, "simulator_seeds": [1]})
