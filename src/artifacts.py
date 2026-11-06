"""Run metadata and run-directory bookkeeping shared by the Phase 2 CLIs.

- `environment()`: Python, platform and package versions.
- `git_state()`: commit hash and whether the working tree is dirty.
- `dataset_hashes()`: SHA-256 of the dataset files (patients.csv, events.csv, meta.json).
- `run_id()`: deterministic id from the config and the dataset hashes, so the same config on the
  same data always has the same id and a changed config or dataset gets a new one.
- `RunRecorder`: refuses to overwrite a completed run unless `overwrite` is set; writes
  `run.json` with status `running` at the start and `complete` or `failed` (with the error)
  at the end, and appends every attempt to `attempts.jsonl` so failed and incomplete runs stay
  on record.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("numpy", "pandas", "scipy", "scikit-learn", "xgboost", "torch", "pyyaml", "matplotlib")
DATASET_FILES = ("patients.csv", "events.csv", "meta.json")
RUNNING, COMPLETE, FAILED = "running", "complete", "failed"


def environment() -> dict[str, Any]:
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {"python": sys.version.split()[0], "platform": platform.platform(), "packages": versions}


def git_state(repo: Path = REPO_ROOT) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()

    try:
        commit, dirty = git("rev-parse", "HEAD"), bool(git("status", "--porcelain"))
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "unknown", "dirty": None}
    return {"commit": commit, "dirty": dirty}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dataset_hashes(directory: Path) -> dict[str, str]:
    return {name: sha256(directory / name) for name in DATASET_FILES if (directory / name).exists()}


def run_id(config: dict[str, Any], data_hashes: dict[str, str]) -> str:
    """`<name>-<10 hex>`: hash of the config (minus `overwrite`) and the dataset hashes."""
    payload = json.dumps({"config": {k: v for k, v in config.items() if k != "overwrite"}, "data": data_hashes},
                         sort_keys=True, default=str)
    return f"{config.get('name', 'run')}-{hashlib.sha256(payload.encode()).hexdigest()[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RunRecorder:
    """Context manager that guards an output directory and records the run's status."""

    def __init__(self, out: Path, info: dict[str, Any], overwrite: bool = False) -> None:
        self.out = Path(out)
        self.info = dict(info)
        self.overwrite = overwrite

    def _write(self) -> None:
        (self.out / "run.json").write_text(json.dumps(self.info, indent=2, default=str), encoding="utf-8")

    def _log_attempt(self) -> None:
        keep = ("run_id", "status", "started_at", "finished_at", "git", "error")
        with (self.out / "attempts.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({k: self.info.get(k) for k in keep}, default=str) + "\n")

    def __enter__(self) -> "RunRecorder":
        previous = self.out / "run.json"
        if previous.exists() and not self.overwrite:
            try:
                status = json.loads(previous.read_text(encoding="utf-8")).get("status", COMPLETE)
            except json.JSONDecodeError:
                status = "unreadable"
            if status == COMPLETE:
                raise FileExistsError(
                    f"{self.out} already holds a completed run; pass --overwrite (or `overwrite: true`) "
                    "or choose another output_dir"
                )
        self.out.mkdir(parents=True, exist_ok=True)
        self.info |= {"status": RUNNING, "started_at": _now(), "finished_at": None, "error": None}
        self._write()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self.info["finished_at"] = _now()
        if exc is None:
            self.info["status"] = COMPLETE
        else:
            self.info["status"] = FAILED
            self.info["error"] = "".join(traceback.format_exception(exc_type, exc, tb))[-4000:]
        self._write()
        self._log_attempt()
        return False


def base_info(config: dict[str, Any], dataset_dir: Path, dataset_meta: dict[str, Any]) -> dict[str, Any]:
    """Metadata common to every Phase 2 run (written to run.json)."""
    hashes = dataset_hashes(dataset_dir)
    git, env = git_state(), environment()
    return {
        "SIMULATED": bool(dataset_meta.get("SIMULATED", False)),
        "run_id": run_id(config, hashes),
        "config": config,
        "git": git,
        "git_commit": git["commit"] + ("-dirty" if git["dirty"] else ""),
        "dataset": str(config.get("dataset")),
        "dataset_hashes": hashes,
        "dataset_git_commit": dataset_meta.get("git_commit"),
        "dataset_experiment_type": dataset_meta.get("experiment_type"),
        "dataset_knowledge_hashes": dataset_meta.get("knowledge_hashes"),
        "simulator_seed": (dataset_meta.get("config") or {}).get("seed"),
        "model_seeds": config.get("seeds"),
        "environment": env,
        "torch_version": env["packages"].get("torch"),
    }
