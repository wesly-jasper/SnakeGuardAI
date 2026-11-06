"""Tests for run metadata and run-directory bookkeeping (src/artifacts.py)."""

import json
from pathlib import Path

import numpy as np
import pytest

from src.artifacts import RunRecorder, dataset_hashes, environment, git_state, run_id
from src.uncertainty.calibration import fit_binary, fit_multiclass


def test_run_id_is_deterministic_and_sensitive() -> None:
    config, data = {"name": "x", "seeds": [0]}, {"patients.csv": "abc"}
    assert run_id(config, data) == run_id(dict(config), dict(data))
    assert run_id(config, data) == run_id(config | {"overwrite": True}, data)  # overwrite flag is not identity
    assert run_id(config, data) != run_id({"name": "x", "seeds": [1]}, data)
    assert run_id(config, data) != run_id(config, {"patients.csv": "abd"})
    assert run_id(config, data).startswith("x-")


def test_recorder_complete_then_refuses_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "run"
    with RunRecorder(out, {"run_id": "a"}) as rec:
        assert json.loads((out / "run.json").read_text())["status"] == "running"
        rec.info["extra"] = 1
    info = json.loads((out / "run.json").read_text())
    assert info["status"] == "complete" and info["extra"] == 1 and info["finished_at"]
    with pytest.raises(FileExistsError):
        with RunRecorder(out, {"run_id": "a"}):
            pass
    with RunRecorder(out, {"run_id": "b"}, overwrite=True):
        pass
    attempts = [json.loads(line) for line in (out / "attempts.jsonl").read_text().splitlines()]
    assert [a["run_id"] for a in attempts] == ["a", "b"]


def test_recorder_records_failure_and_allows_rerun(tmp_path: Path) -> None:
    out = tmp_path / "run"
    with pytest.raises(RuntimeError):
        with RunRecorder(out, {"run_id": "a"}):
            raise RuntimeError("boom")
    info = json.loads((out / "run.json").read_text())
    assert info["status"] == "failed" and "boom" in info["error"]
    with RunRecorder(out, {"run_id": "a"}):  # a failed run may be replaced without --overwrite
        pass
    statuses = [json.loads(line)["status"] for line in (out / "attempts.jsonl").read_text().splitlines()]
    assert statuses == ["failed", "complete"]


def test_environment_git_and_hashes(tmp_path: Path) -> None:
    env = environment()
    assert env["python"] and env["packages"]["numpy"]
    assert set(git_state()) == {"commit", "dirty"}
    (tmp_path / "patients.csv").write_text("a\n")
    hashes = dataset_hashes(tmp_path)
    assert list(hashes) == ["patients.csv"] and len(hashes["patients.csv"]) == 64


def test_platt_with_single_class_is_identity() -> None:
    p = np.array([[0.7, 0.3], [0.6, 0.4], [0.9, 0.1]])
    cal = fit_multiclass("sigmoid", p, np.zeros(3, int))
    assert cal.params["per_class"][0]["identity_single_class"]
    np.testing.assert_allclose(cal.apply(p), p)
    np.testing.assert_allclose(fit_binary("sigmoid", p[:, 0], np.ones(3, int)).apply(p[:, 0]), p[:, 0])
