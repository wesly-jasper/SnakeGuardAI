"""Phase 2 simulator-seed variability: the same models on independently simulated datasets.

    python -m src.seed_variability --config configs/phase2_simseed_sim_v2.yaml

For each simulator seed the base dataset config (e.g. configs/sim_v2.yaml) is regenerated with
only the seed changed (same knowledge, assumptions and experiment type), and the Phase 2 training
run (src/train.py) is repeated on it with the same model seeds. Three sources of variation are
kept apart:

- model randomness: sd over model (training) seeds on one dataset, averaged over datasets;
- population variability: sd / range over simulator seeds of the per-dataset mean (this also
  contains test-set sampling, because every simulated dataset has its own test patients);
- evaluation uncertainty: bootstrap sd of the test metric for one dataset and one model seed
  (resampling test patients), averaged over datasets.

Simulator seed = the dataset; model seed = training randomness; they are never mixed. Writes
seed_variability.json, per_run.csv, run.json and report.md to `output_dir`, and one full training
run (all Phase 2 artifacts) per simulator seed under `output_dir/sim_seed_<s>/`.
All numbers are SIMULATION results.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.artifacts import RunRecorder, base_info, dataset_hashes
from src.data.dataset import resolve
from src.data.generate import generate
from src.data.generate import load_config as load_data_config
from src.evaluate import DRY_INDEX, critical_error_rate, expected_calibration_error
from src.reporting import HEADER, RESEARCH_ONLY, table
from src.train import load_config as check_train_config
from src.train import run as train_run

METRICS = ("macro_f1", "critical_error_rate", "accuracy", "envenomation_sensitivity",
           "envenomation_specificity", "nll", "ece", "brier")
BOOTSTRAP_METRICS = ("macro_f1", "critical_error_rate", "ece")


def dataset_config(base: dict[str, Any], seed: int, data_dir: Path, n_patients: int | None) -> dict[str, Any]:
    """The base dataset config with only the seed (and output folder, optional size) changed."""
    config = copy.deepcopy(base)
    config["seed"] = int(seed)
    config["name"] = f"{base['name']}__sim_seed_{seed}"
    config["output_dir"] = str(data_dir / f"sim_seed_{seed}")
    if n_patients is not None:
        config["n_patients"] = int(n_patients)
    return config


def train_config(config: dict[str, Any], seed: int, dataset: Path) -> dict[str, Any]:
    out = {
        "name": f"{config['name']}__sim_seed_{seed}",
        "dataset": str(dataset),
        "output_dir": str(resolve(config["output_dir"]) / f"sim_seed_{seed}"),
        "seeds": list(config["model_seeds"]),
        "validation_fraction": config.get("validation_fraction", 0.15),
        "torch_threads": config.get("torch_threads", 4),
        "decision_thresholds": config.get("decision_thresholds"),
        "calibration": config.get("calibration"),
        "models": config["models"],
    }
    return {k: v for k, v in out.items() if v is not None}


def bootstrap_sd(y: np.ndarray, pred: np.ndarray, proba: np.ndarray | None, n_boot: int, seed: int) -> dict[str, float]:
    """Sd of test metrics over bootstrap resamples of test patients (evaluation uncertainty)."""
    from sklearn.metrics import f1_score

    rng = np.random.default_rng([seed, 7])
    values: dict[str, list[float]] = {k: [] for k in BOOTSTRAP_METRICS}
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        values["macro_f1"].append(f1_score(y[idx], pred[idx], labels=list(range(4)), average="macro", zero_division=0))
        values["critical_error_rate"].append(critical_error_rate(y[idx], pred[idx], DRY_INDEX))
        if proba is not None:
            values["ece"].append(expected_calibration_error(proba[idx], y[idx]))
    return {k: float(np.nanstd(v)) if v else float("nan") for k, v in values.items()}


def collect(metrics: dict[str, Any], run_dir: Path, sim_seed: int, n_boot: int) -> list[dict[str, Any]]:
    """One row per (model, model seed): test metrics plus bootstrap sds for the first model seed."""
    rows = []
    for model, res in metrics.items():
        for i, r in enumerate(res["runs"]):
            row = {"sim_seed": sim_seed, "model": model, "model_seed": r["seed"]}
            row |= {k: r["metrics"]["syndrome"].get(k, float("nan")) for k in METRICS}
            if i == 0 and n_boot:
                data = np.load(run_dir / f"predictions_{model}_seed{r['seed']}.npz")
                test = data["split"] == "test"
                proba = data["p_syndrome"][test] if "p_syndrome" in data.files else None
                boot = bootstrap_sd(data["y_syndrome"][test], data["pred_syndrome"][test], proba, n_boot, sim_seed)
                row |= {f"boot_sd_{k}": v for k, v in boot.items()}
            rows.append(row)
    return rows


def decompose(per_run: pd.DataFrame) -> dict[str, Any]:
    """Model-seed, simulator-seed and bootstrap components per model and metric."""
    out: dict[str, Any] = {}
    for model, rows in per_run.groupby("model", sort=False):
        per_dataset = rows.groupby("sim_seed")
        entry: dict[str, Any] = {"n_sim_seeds": int(rows["sim_seed"].nunique()),
                                 "n_model_seeds": int(rows.groupby("sim_seed").size().max())}
        for metric in METRICS:
            means = per_dataset[metric].mean()
            model_sd = per_dataset[metric].std(ddof=0)
            boot = rows.get(f"boot_sd_{metric}")
            entry[metric] = {
                "mean": float(means.mean()),
                "sim_seed_sd": float(means.std(ddof=1)) if len(means) > 1 else float("nan"),
                "sim_seed_min": float(means.min()), "sim_seed_max": float(means.max()),
                "model_seed_sd": float(model_sd.mean()),
                "bootstrap_sd": float(boot.dropna().mean()) if boot is not None and boot.notna().any() else None,
                "per_sim_seed": {int(k): float(v) for k, v in means.items()},
            }
        out[str(model)] = entry
    return out


def run(config: dict[str, Any], overwrite: bool = False) -> Path:
    for key in ("name", "base_config", "simulator_seeds", "model_seeds", "models", "data_dir", "output_dir"):
        if key not in config:
            raise ValueError(f"config missing required key: {key}")
    if len(set(config["simulator_seeds"])) != len(config["simulator_seeds"]) or len(config["simulator_seeds"]) < 2:
        raise ValueError("simulator_seeds must hold at least two distinct seeds")
    base = load_data_config(resolve(config["base_config"]))
    data_dir, out = resolve(config["data_dir"]), resolve(config["output_dir"])
    n_boot = int(config.get("bootstrap", 200))
    first_data = None
    rows: list[dict[str, Any]] = []
    datasets: dict[int, dict[str, Any]] = {}
    for seed in config["simulator_seeds"]:
        dataset = generate(dataset_config(base, seed, data_dir, config.get("n_patients")))
        first_data = first_data or dataset
        tconfig = train_config(config, seed, dataset)
        check_train_config_dict(tconfig)
        run_dir = train_run(tconfig, overwrite=overwrite)
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        rows += collect(metrics, run_dir, int(seed), n_boot)
        meta = json.loads((dataset / "meta.json").read_text(encoding="utf-8"))
        datasets[int(seed)] = {"dataset": str(dataset), "hashes": dataset_hashes(dataset),
                               "syndrome_counts": meta["syndrome_counts"],
                               "run_id": json.loads((run_dir / "run.json").read_text())["run_id"]}
        print(f"simulator seed {seed}: done")
    per_run = pd.DataFrame(rows)
    info = base_info({**config, "dataset": config["data_dir"]}, first_data, {"SIMULATED": True}) | {
        "simulator_seeds": config["simulator_seeds"], "datasets": datasets,
        "base_dataset_config": base, "bootstrap": n_boot,
    }
    with RunRecorder(out, info, overwrite=overwrite) as recorder:
        results = decompose(per_run)
        per_run.to_csv(out / "per_run.csv", index=False)
        (out / "seed_variability.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        (out / "report.md").write_text(render(results, recorder.info), encoding="utf-8")
    return out


def check_train_config_dict(config: dict[str, Any]) -> None:
    """Validate a generated training config with the same checks as src.train.load_config."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "c.yaml"
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        check_train_config(path)


def _cell(m: dict[str, Any], digits: int = 3) -> str:
    return f"{m['mean']:.{digits}f}"


def render(results: dict[str, Any], info: dict[str, Any]) -> str:
    rows = []
    for model, entry in results.items():
        for metric in ("macro_f1", "critical_error_rate", "ece"):
            m = entry[metric]
            rows.append({
                "model": model, "metric": metric, "mean": _cell(m),
                "simulator-seed sd": f"{m['sim_seed_sd']:.4f}",
                "simulator-seed range": f"{m['sim_seed_min']:.3f}-{m['sim_seed_max']:.3f}",
                "model-seed sd": f"{m['model_seed_sd']:.4f}",
                "test bootstrap sd": "-" if m["bootstrap_sd"] is None else f"{m['bootstrap_sd']:.4f}",
            })
    config = info["config"]
    return "\n".join([
        f"# Phase 2 simulator-seed variability (`{config['name']}`)\n",
        HEADER, RESEARCH_ONLY,
        f"- base dataset config `{config['base_config']}`, regenerated with simulator seeds "
        f"{config['simulator_seeds']} (only the seed changes); model seeds {config['model_seeds']} on every dataset.",
        f"- commit `{info['git_commit']}`, run id `{info['run_id']}`.",
        "- **simulator-seed sd / range**: spread of the per-dataset mean (over model seeds) across independently "
        "simulated datasets. Each dataset has its own test patients, so this includes test-set sampling.",
        "- **model-seed sd**: spread over training seeds on one dataset, averaged over datasets.",
        f"- **test bootstrap sd**: resampling the test patients ({info['bootstrap']} resamples) for one dataset "
        "and the first model seed, averaged over datasets.",
        "- None of these covers uncertainty in the knowledge table itself or differences between the simulator "
        "and real patients.\n",
        table(rows),
        "",
    ])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    parser.add_argument("--overwrite", action="store_true", help="replace completed per-seed runs")
    args = parser.parse_args(argv)
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    print(f"wrote results to {run(config, overwrite=args.overwrite)}")


if __name__ == "__main__":
    main()
