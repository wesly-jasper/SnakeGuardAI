"""End-to-end test of the Phase 2 training CLI on a tiny simulated dataset."""

import json
from pathlib import Path

import numpy as np
import yaml

from src.data.generate import generate
from src.evaluate import evaluate_predictions
from src.train import load_config, main


def test_train_cli_writes_metrics_report_and_predictions(knowledge_dir: Path, tmp_path: Path) -> None:
    data = generate({
        "name": "t", "seed": 3, "n_patients": 600, "knowledge_dir": str(knowledge_dir),
        "output_dir": str(tmp_path / "sim"), "presentation_hours": [0.5, 4.0],
    })
    config = {
        "name": "t2", "dataset": str(data), "output_dir": str(tmp_path / "run"), "seeds": [0, 1],
        "torch_threads": 1,
        "models": {
            "prior": {}, "rule": {},
            "xgboost": {"params": {"n_estimators": 20, "early_stopping_rounds": 5}},
            "xgboost_context": {"params": {"n_estimators": 20, "early_stopping_rounds": 5}},
            "transformer": {"d_model": 16, "n_heads": 2, "n_layers": 1, "max_epochs": 3, "batch_size": 64},
        },
    }
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(config))
    main(["--config", str(path)])

    out = tmp_path / "run"
    metrics = json.loads((out / "metrics.json").read_text())
    assert set(metrics) == set(config["models"])
    assert len(metrics["transformer"]["runs"]) == 2 and len(metrics["rule"]["runs"]) == 1
    assert "species" not in metrics["rule"]["summary"]
    assert 0 <= metrics["xgboost"]["summary"]["syndrome"]["critical_error_rate"]["mean"] <= 1
    assert "SIMULATION RESULTS" in (out / "report.md").read_text(encoding="utf-8")
    run = json.loads((out / "run.json").read_text())
    assert run["SIMULATED"] is True and run["git_commit"]

    saved = np.load(out / "predictions_transformer_seed0.npz")
    assert set(saved["split"]) == {"calibration", "test"}  # train patients are never saved
    np.testing.assert_allclose(saved["p_syndrome"].sum(1), 1.0, atol=1e-5)
    recomputed = evaluate_predictions(out / "predictions_xgboost_seed1.npz")
    assert recomputed["syndrome"]["macro_f1"] == metrics["xgboost"]["runs"][1]["metrics"]["syndrome"]["macro_f1"]


def test_config_rejects_unknown_model(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump({"name": "x", "dataset": "d", "output_dir": "o", "seeds": [0], "models": {"svm": {}}}))
    try:
        load_config(path)
    except ValueError as e:
        assert "svm" in str(e)
    else:
        raise AssertionError("expected ValueError")
