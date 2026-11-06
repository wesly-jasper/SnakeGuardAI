"""Robustness to imperfect symptom reporting (Phase 2). SIMULATION results only.

    python -m src.robustness --config configs/phase2_robustness_sim_v2.yaml

Models are trained once per seed on the CLEAN training inputs. Corruption is then applied
to a copy of the evaluation inputs only; the dataset on disk and the clean inputs are never
modified. Corruption types (level = probability or relative size):

- `missing_symptom`: each observed event is dropped with probability `level` (random loss).
- `omission`: events of patient-reported symptoms (`omission_symptoms`, by default local
  pain, abdominal pain, vomiting, headache: symptoms a patient may not mention, as opposed
  to signs a clinician examines) are dropped with probability `level`. This choice of
  symptoms is an ASSUMPTION.
- `false_report`: with probability `level` a patient reports one extra symptom they do not
  have, drawn uniformly from the symptoms ever observed in the training inputs, with an onset
  uniform between the bite and presentation.
- `onset_noise`: each onset time gets Gaussian error with sd = `level` x presentation time,
  clipped to [0, presentation].
- `missing_presentation`: the presentation time is unknown (NaN) with probability `level`.
  Only models that can take a missing value are evaluated (prior, rule, XGBoost via its
  native missing-value handling, although it never saw one in training); the others are
  reported as not supported.

Patient groups for "no observed symptom" are fixed on the clean inputs. Writes
`robustness.json`, `run.json` and `report.md` to `output_dir`.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml

from src.artifacts import RunRecorder, base_info
from src.data.dataset import load_dataset, resolve
from src.data.features import ModelInputs, build_inputs
from src.data.splits import split_summary
from src.decision_policy import DEFAULT_THRESHOLDS, validate_thresholds
from src.models.registry import resolve_model
from src.reporting import HEADER, RESEARCH_ONLY, fmt
from src.train import evaluate_run, fit_for_seed

DEFAULT_LEVELS: tuple[float, ...] = (0.0, 0.05, 0.1, 0.2, 0.3)
DEFAULT_OMISSION_SYMPTOMS: tuple[str, ...] = ("local_pain", "abdominal_pain", "vomiting", "headache")
SUMMARY_KEYS: tuple[str, ...] = ("macro_f1", "critical_error_rate", "envenomation_sensitivity",
                                 "envenomation_specificity", "ece", "nll")


def _check_level(level: float) -> float:
    level = float(level)
    if not 0.0 <= level <= 1.0:
        raise ValueError("corruption level must be in [0, 1]")
    return level


def _resorted(seq: np.ndarray) -> np.ndarray:
    return seq[np.lexsort((seq[:, 0], seq[:, 1]))] if len(seq) else seq


def drop_events(inputs: ModelInputs, level: float, rng: np.random.Generator,
                eligible: frozenset[int] | None = None) -> ModelInputs:
    """Drop each (eligible) observed event with probability `level`."""
    level = _check_level(level)
    out = []
    for seq in inputs.sequences:
        if not len(seq):
            out.append(seq.copy())
            continue
        candidates = np.ones(len(seq), dtype=bool) if eligible is None else np.isin(seq[:, 0].astype(int), list(eligible))
        drop = candidates & (rng.random(len(seq)) < level)
        out.append(seq[~drop].copy())
    return replace(inputs, sequences=tuple(out))


def omit_reported(inputs: ModelInputs, level: float, rng: np.random.Generator,
                  symptoms: tuple[str, ...] = DEFAULT_OMISSION_SYMPTOMS) -> ModelInputs:
    unknown = set(symptoms) - set(inputs.symptoms)
    if unknown:
        raise ValueError(f"omission symptoms not in vocabulary: {sorted(unknown)}")
    eligible = frozenset(inputs.symptoms.index(s) for s in symptoms)
    return drop_events(inputs, level, rng, eligible)


def false_reports(inputs: ModelInputs, level: float, rng: np.random.Generator, pool: tuple[int, ...]) -> ModelInputs:
    """With probability `level`, add one symptom the patient does not have, onset uniform in [0, presentation]."""
    level = _check_level(level)
    if not pool:
        raise ValueError("false-report pool is empty")
    out = []
    for seq, presentation in zip(inputs.sequences, inputs.presentation):
        have = set(seq[:, 0].astype(int)) if len(seq) else set()
        options = [s for s in pool if s not in have]
        if options and np.isfinite(presentation) and rng.random() < level:
            extra = np.array([[rng.choice(options), rng.uniform(0.0, presentation)]])
            seq = _resorted(np.vstack([seq, extra]))
        out.append(seq.copy())
    return replace(inputs, sequences=tuple(out))


def onset_noise(inputs: ModelInputs, level: float, rng: np.random.Generator) -> ModelInputs:
    """Gaussian onset error with sd = level x presentation time, clipped to [0, presentation]."""
    level = _check_level(level)
    out = []
    for seq, presentation in zip(inputs.sequences, inputs.presentation):
        seq = seq.copy()
        if len(seq) and level > 0 and np.isfinite(presentation):
            noisy = seq[:, 1] + rng.normal(0.0, level * presentation, len(seq))
            seq[:, 1] = np.clip(noisy, 0.0, presentation)
            seq = _resorted(seq)
        out.append(seq)
    return replace(inputs, sequences=tuple(out))


def missing_presentation(inputs: ModelInputs, level: float, rng: np.random.Generator) -> ModelInputs:
    level = _check_level(level)
    presentation = inputs.presentation.copy()
    presentation[rng.random(len(presentation)) < level] = np.nan
    return replace(inputs, presentation=presentation)


def corruptions(train_inputs: ModelInputs, train_mask: np.ndarray, omission_symptoms: tuple[str, ...],
                ) -> dict[str, Callable[[ModelInputs, float, np.random.Generator], ModelInputs]]:
    seen = np.concatenate([train_inputs.sequences[i][:, 0] for i in np.flatnonzero(train_mask)] or [np.zeros(0)])
    pool = tuple(int(i) for i in np.unique(seen.astype(int)))
    return {
        "missing_symptom": drop_events,
        "omission": lambda x, level, rng: omit_reported(x, level, rng, omission_symptoms),
        "false_report": lambda x, level, rng: false_reports(x, level, rng, pool),
        "onset_noise": onset_noise,
        "missing_presentation": missing_presentation,
    }


def load_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key in ("name", "dataset", "output_dir", "seeds", "models"):
        if key not in config:
            raise ValueError(f"config missing required key: {key}")
    for name, entry in config["models"].items():
        resolve_model(name, entry)
    for level in config.get("levels", DEFAULT_LEVELS):
        _check_level(level)
    return config


def run(config: dict[str, Any], overwrite: bool = False) -> Path:
    ds = load_dataset(config["dataset"])
    out = resolve(config["output_dir"])
    info = base_info(config, resolve(config["dataset"]), ds.meta) | {"splits": split_summary(ds.patients)}
    with RunRecorder(out, info, overwrite or bool(config.get("overwrite", False))) as recorder:
        _run(config, ds, out, recorder.info)
    return out


def _run(config: dict[str, Any], ds: Any, out: Path, run_info: dict[str, Any]) -> None:
    clean = build_inputs(ds)
    n_observed = clean.n_observed
    test = ds.split_mask("test")
    levels = [_check_level(v) for v in config.get("levels", DEFAULT_LEVELS)]
    thresholds = validate_thresholds(config.get("decision_thresholds", DEFAULT_THRESHOLDS))
    torch.set_num_threads(int(config.get("torch_threads", 4)))
    corrupt = corruptions(clean, ds.split_mask("train"),
                          tuple(config.get("omission_symptoms", DEFAULT_OMISSION_SYMPTOMS)))
    selected = config.get("corruptions", list(corrupt))
    unknown = set(selected) - set(corrupt)
    if unknown:
        raise ValueError(f"unknown corruptions: {sorted(unknown)}")
    results: dict[str, Any] = {}
    for name, entry in config["models"].items():
        spec = resolve_model(name, entry)
        seeds = config["seeds"] if spec.learned else [config["seeds"][0]]
        cells: dict[str, dict[str, list[dict[str, Any]]]] = {c: {str(v): [] for v in levels} for c in selected}
        for seed in seeds:
            model = fit_for_seed(spec, ds, clean, int(seed), float(config.get("validation_fraction", 0.15)))
            for ci, kind in enumerate(selected):
                for li, level in enumerate(levels):
                    rng = np.random.default_rng([int(seed), ci, li, 7])
                    noisy = corrupt[kind](clean, level, rng)
                    try:
                        prediction = model.predict(noisy)
                    except ValueError as err:
                        if "missing presentation" not in str(err):
                            raise
                        cells[kind][str(level)].append({"seed": seed, "supported": False})
                        continue
                    metrics = evaluate_run(ds.syndrome_index, ds.species_index, n_observed, prediction, test, thresholds)
                    metrics["visible_events_test"] = int(noisy.n_observed[test].sum())
                    cells[kind][str(level)].append({"seed": seed, "supported": True, "metrics": metrics})
            print(f"{name} seed {seed}: done")
        results[name] = {"kind": spec.kind, "cells": cells, "summary": summarise_cells(cells)}
    run_info |= {"levels": levels, "clean_visible_events_test": int(n_observed[test].sum())}
    (out / "robustness.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "report.md").write_text(render(results, run_info, selected), encoding="utf-8")


def summarise_cells(cells: dict[str, dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for kind, by_level in cells.items():
        summary[kind] = {}
        for level, runs in by_level.items():
            ok = [r["metrics"] for r in runs if r["supported"]]
            if not ok:
                summary[kind][level] = None
                continue
            cell = {}
            for key in SUMMARY_KEYS:
                values = np.array([m["syndrome"].get(key, np.nan) for m in ok], dtype=float)
                cell[key] = {"mean": float(np.nanmean(values)) if not np.isnan(values).all() else float("nan"),
                             "sd": float(np.nanstd(values)) if not np.isnan(values).all() else float("nan")}
            no_obs = np.array([m["critical_error"]["no_observed_symptom"]["rate"] for m in ok], dtype=float)
            cell["critical_error_no_observed"] = {"mean": float(np.mean(no_obs)), "sd": float(np.std(no_obs))}
            cell["visible_events_test"] = float(np.mean([m["visible_events_test"] for m in ok]))
            summary[kind][level] = cell
    return summary


def render(results: dict[str, Any], run_info: dict[str, Any], selected: list[str]) -> str:
    config = run_info["config"]
    levels = [str(v) for v in run_info["levels"]]
    parts = [
        f"# Phase 2 robustness to imperfect symptom reporting on `{config['dataset']}`\n",
        HEADER if run_info["SIMULATED"] else "", RESEARCH_ONLY,
        f"- run `{config['name']}`, commit `{run_info['git_commit']}`; seeds {config['seeds']} (training seed and "
        "corruption draw), mean ± sd. Models trained on clean inputs; only test-time inputs are corrupted.",
        f"- clean test inputs contain {run_info['clean_visible_events_test']} visible symptom events.",
        "- `n/s` = model cannot take a missing presentation time. Omission symptoms (assumption): "
        f"{', '.join(config.get('omission_symptoms', DEFAULT_OMISSION_SYMPTOMS))}.",
    ]
    for metric, title in (("macro_f1", "macro-F1"), ("critical_error_rate", "critical error"),
                          ("critical_error_no_observed", "critical error, patients with no observed symptom (clean)"),
                          ("ece", "ECE")):
        parts.append(f"\n## {title}\n")
        for kind in selected:
            rows = []
            for name, res in results.items():
                row = {"model": name}
                for level in levels:
                    cell = res["summary"][kind][level]
                    row[f"level {level}"] = "n/s" if cell is None else fmt(cell.get(metric))
                rows.append(row)
            parts += [f"\n### {kind}\n", pd.DataFrame(rows).to_markdown(index=False)]
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    parser.add_argument("--overwrite", action="store_true", help="replace a completed run in output_dir")
    args = parser.parse_args(argv)
    print(f"wrote results to {run(load_config(args.config), overwrite=args.overwrite)}")


if __name__ == "__main__":
    main()
