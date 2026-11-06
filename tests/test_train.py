"""End-to-end test of the Phase 2 training CLI on a tiny simulated dataset."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.data.generate import generate
from src.evaluate import evaluate_predictions
from src.train import load_config, main
from src.verify_runs import verify_run


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

    # calibration: fitted on the calibration split, raw and calibrated metrics both kept and regenerable
    cal = metrics["xgboost"]["runs"][1]["calibration"]
    assert cal["fitted_on"] == "calibration split" and cal["n_eval"] == int((saved["split"] == "test").sum())
    for target in ("syndrome", "envenomed"):
        assert "raw" in cal[target] and "temperature" in cal[target]
        for method, values in recomputed["calibration"][target].items():
            assert values["nll"] == cal[target][method]["nll"]
    assert "isotonic" in cal["skipped"]  # calibration split of 120 is too small
    assert "p_syndrome_temperature" in saved.files and "p_envenomed_raw" in saved.files
    assert "calibration" in metrics["xgboost"]["summary"]

    # run metadata
    assert run["status"] == "complete" and run["run_id"].startswith("t2-")
    assert run["git"]["commit"] and run["git"]["dirty"] in (True, False)
    assert run["simulator_seed"] == 3 and run["model_seeds"] == [0, 1]
    assert set(run["dataset_hashes"]) == {"patients.csv", "events.csv", "meta.json"}
    assert run["feature_allowlist"]["input_columns"] == ["presentation_hours"]
    assert run["model_inputs"]["xgboost"] == metrics["xgboost"]["features"]
    splits = run["splits"]["splits"]
    assert sum(s["n"] for s in splits.values()) == 600
    assert run["environment"]["packages"]["xgboost"]
    assert "metrics.json" in run["artifacts"] and "predictions_xgboost_seed1.npz" in run["artifacts"]
    assert len((out / "attempts.jsonl").read_text().splitlines()) == 1

    if importlib.util.find_spec("matplotlib"):
        assert (out / "reliability_xgboost_seed0.png").exists()

    # the run verifier finds no leakage, wrong splits or unreproducible metrics
    report = verify_run(out)
    assert report["problems"] == [] and report["prediction_files_checked"] == 8
    assert report["commit_matches_head"]
    # and it does catch a tampered metric
    tampered = json.loads((out / "metrics.json").read_text())
    tampered["xgboost"]["runs"][0]["metrics"]["syndrome"]["macro_f1"] += 0.01
    (out / "metrics.json").write_text(json.dumps(tampered))
    assert any("macro_f1" in p for p in verify_run(out)["problems"])

    # a completed run is never overwritten by accident
    with pytest.raises(FileExistsError):
        main(["--config", str(path)])


def test_config_rejects_unknown_model(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump({"name": "x", "dataset": "d", "output_dir": "o", "seeds": [0], "models": {"svm": {}}}))
    try:
        load_config(path)
    except ValueError as e:
        assert "svm" in str(e)
    else:
        raise AssertionError("expected ValueError")
