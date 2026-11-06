"""Phase 2 explainability for the tabular models (XGBoost, random forest). SIMULATION only.

    python -m src.explain --config configs/phase2_explain_sim_v2.yaml

Models are fitted exactly as in src/train.py (train split minus validation, one model seed);
explanations are computed on test-split inputs (no refitting, no labels used except for
permutation importance scores). Methods:

- XGBoost: exact TreeSHAP from XGBoost itself (`pred_contribs=True`), per class, on the
  log-odds (margin) scale. Additive: bias + sum of contributions = the model's margin.
- Random forest: tree-path contributions (Saabas method) on the probability scale, exact for
  the forest (bias + sum = predicted probability) but NOT Shapley values.
- Both: permutation importance on test (drop in macro-F1 and rise in NLL when a feature or a
  feature group is shuffled across patients), averaged over `n_repeats`.

Features are grouped by block (symptom identity = `present_*`, timing = `onset_*`/`since_*`,
presentation delay, symptom count, context) and by symptom (all columns of one symptom).
Global summaries and individual explanations for a fixed, label-stratified set of test
patients are written as JSON/CSV (and PNG if matplotlib is installed).

These describe what a model learned from SIMULATED data generated from the knowledge table.
They are not causal and not clinical evidence; a symptom ranking here mainly reflects how the
simulator encodes that symptom (frequency, cited onset window, label-only status).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy import sparse
from sklearn.metrics import f1_score

from src.artifacts import RunRecorder, base_info
from src.data.dataset import SymptomDataset, load_dataset, resolve
from src.data.features import CONTEXT_FEATURE_NAMES, build_inputs, tabular_matrix
from src.data.simulator import SYNDROMES
from src.evaluate import negative_log_likelihood
from src.models.registry import TabularModel, resolve_model
from src.reporting import HEADER, RESEARCH_ONLY, table
from src.train import fit_for_seed

SUPPORTED = ("xgboost", "random_forest")
DISCLAIMER = ("Explanations describe associations a model learned from SIMULATED data. They are not causal "
              "and not clinical evidence.")


def feature_group(name: str) -> str:
    """Block a tabular feature belongs to."""
    if name.startswith("present_"):
        return "symptom_identity"
    if name.startswith(("onset_", "since_")) or (name.startswith("event") and name.endswith(("_onset", "_since"))):
        return "timing"
    if name == "presentation_hours":
        return "presentation_delay"
    if name == "n_observed":
        return "symptom_count"
    if name in CONTEXT_FEATURE_NAMES:
        return "context"
    raise ValueError(f"feature {name!r} has no explanation group")


def feature_symptom(name: str) -> str | None:
    for prefix in ("present_", "onset_", "since_"):
        if name.startswith(prefix):
            return name[len(prefix):]
    return None


def groups_of(names: list[str], by: str) -> dict[str, list[int]]:
    """Column indices per group; `by` is `block` or `symptom` (non-symptom columns keep their block)."""
    out: dict[str, list[int]] = {}
    for i, name in enumerate(names):
        key = feature_group(name) if by == "block" else (feature_symptom(name) or feature_group(name))
        out.setdefault(key, []).append(i)
    return out


def xgb_contributions(head: Any, x: np.ndarray, n_classes: int) -> tuple[np.ndarray, np.ndarray]:
    """TreeSHAP per class: (contrib[n, class, feature], bias[n, class]) on the margin scale.

    Classes absent from training get zeros. Binary models (2 trained classes) are expanded to
    two columns with opposite signs."""
    import xgboost as xgb

    raw = head.model.get_booster().predict(xgb.DMatrix(x), pred_contribs=True,
                                           iteration_range=(0, head.model.best_iteration + 1))
    if raw.ndim == 2:  # binary: one margin for the second class
        raw = np.stack([-raw, raw], axis=1)
    contrib = np.zeros((len(x), n_classes, x.shape[1]))
    bias = np.zeros((len(x), n_classes))
    contrib[:, head.classes_, :] = raw[:, :, :-1]
    bias[:, head.classes_] = raw[:, :, -1]
    return contrib, bias


def forest_contributions(head: Any, x: np.ndarray, n_classes: int) -> tuple[np.ndarray, np.ndarray]:
    """Saabas tree-path contributions per class on the probability scale (not Shapley values)."""
    imputer, forest = head.model[0], head.model[-1]
    xi = imputer.transform(x)
    n, f = xi.shape
    k = len(forest.classes_)
    contrib, bias = np.zeros((n, f * k)), np.zeros((n, k))
    for tree in forest.estimators_:
        t = tree.tree_
        value = t.value[:, 0, :] / t.value[:, 0, :].sum(1, keepdims=True)
        parent = np.full(t.node_count, -1)
        for node in range(t.node_count):
            for child in (t.children_left[node], t.children_right[node]):
                if child >= 0:
                    parent[child] = node
        delta = np.zeros((t.node_count, f * k))
        for node in range(1, t.node_count):
            p = parent[node]
            feat = t.feature[p]
            delta[node, feat * k:(feat + 1) * k] = value[node] - value[p]
        path = sparse.csr_matrix(tree.decision_path(xi))
        contrib += path @ delta
        bias += value[0]
    contrib = (contrib / len(forest.estimators_)).reshape(n, f, k).transpose(0, 2, 1)
    bias /= len(forest.estimators_)
    full_c, full_b = np.zeros((n, n_classes, f)), np.zeros((n, n_classes))
    cls = forest.classes_.astype(int)
    full_c[:, cls, :], full_b[:, cls] = contrib, bias
    return full_c, full_b


def contributions(model: TabularModel, x: np.ndarray) -> tuple[np.ndarray, np.ndarray, str]:
    head = model.heads["syndrome"]
    if model.spec.kind == "xgboost":
        return (*xgb_contributions(head, x, len(SYNDROMES)), "TreeSHAP (exact, log-odds scale)")
    if model.spec.kind == "random_forest":
        return (*forest_contributions(head, x, len(SYNDROMES)),
                "tree-path contributions (Saabas; probability scale; not Shapley values)")
    raise ValueError(f"explanations support {SUPPORTED}, not {model.spec.kind!r}")


def permutation_importance(
    model: TabularModel, x: np.ndarray, y: np.ndarray, groups: dict[str, list[int]], n_repeats: int, seed: int,
) -> dict[str, dict[str, float]]:
    """Drop in macro-F1 and rise in NLL when each group's columns are shuffled jointly."""
    head = model.heads["syndrome"]
    labels = list(range(len(SYNDROMES)))

    def score(xx: np.ndarray) -> tuple[float, float]:
        p = head.predict_proba(xx)
        return f1_score(y, p.argmax(1), labels=labels, average="macro", zero_division=0), negative_log_likelihood(p, y)

    base_f1, base_nll = score(x)
    rng = np.random.default_rng([seed, 11])
    out = {}
    for name, cols in groups.items():
        f1s, nlls = [], []
        for _ in range(n_repeats):
            xp = x.copy()
            xp[:, cols] = x[rng.permutation(len(x))][:, cols]
            f1, nll = score(xp)
            f1s.append(base_f1 - f1)
            nlls.append(nll - base_nll)
        out[name] = {"macro_f1_drop": float(np.mean(f1s)), "macro_f1_drop_sd": float(np.std(f1s)),
                     "nll_rise": float(np.mean(nlls)), "nll_rise_sd": float(np.std(nlls))}
    return out


def global_importance(contrib: np.ndarray, groups: dict[str, list[int]]) -> dict[str, dict[str, float]]:
    """Mean |group contribution| per class (group contribution = sum of its columns) and summed."""
    out = {}
    for name, cols in groups.items():
        per_class = np.abs(contrib[:, :, cols].sum(axis=2)).mean(axis=0)
        out[name] = {label: float(v) for label, v in zip(SYNDROMES, per_class)} | {"all_classes": float(per_class.sum())}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["all_classes"]))


def pick_examples(ds: SymptomDataset, test_idx: np.ndarray, n_observed: np.ndarray) -> list[int]:
    """Deterministic examples: per true syndrome the first test patient with a symptom observed,
    plus the first with nothing observed."""
    y = ds.syndrome_index
    chosen = []
    for c in range(len(SYNDROMES)):
        hit = [i for i in test_idx if y[i] == c and n_observed[i] > 0]
        if hit:
            chosen.append(int(hit[0]))
    none = [i for i in test_idx if n_observed[i] == 0]
    if none:
        chosen.append(int(none[0]))
    return chosen


def individual(
    contrib: np.ndarray, bias: np.ndarray, proba: np.ndarray, x: np.ndarray, names: list[str], rows: list[int],
    patient_ids: np.ndarray, y: np.ndarray, top: int = 8,
) -> list[dict[str, Any]]:
    """Top contributions toward the predicted class for each example (test-row positions in `rows`)."""
    out = []
    for r in rows:
        pred = int(proba[r].argmax())
        c = contrib[r, pred]
        order = np.argsort(-np.abs(c))[:top]
        out.append({
            "patient_id": int(patient_ids[r]), "true": SYNDROMES[int(y[r])], "predicted": SYNDROMES[pred],
            "p_predicted": float(proba[r, pred]), "p_envenomed": float(1 - proba[r, -1]),
            "bias": float(bias[r, pred]), "sum_contributions": float(c.sum()),
            "top": [{"feature": names[i], "value": None if np.isnan(x[r, i]) else float(x[r, i]),
                     "contribution": float(c[i])} for i in order if c[i] != 0],
        })
    return out


def plot_groups(results: dict[str, Any], path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    models = list(results)
    fig, axes = plt.subplots(1, len(models), figsize=(4.5 * len(models), 3.2), squeeze=False)
    for ax, name in zip(axes[0], models):
        perm = results[name]["permutation_block"]
        keys = sorted(perm, key=lambda k: perm[k]["macro_f1_drop"])
        ax.barh(keys, [perm[k]["macro_f1_drop"] for k in keys], color="#4C72B0")
        ax.set_title(f"{name}: macro-F1 drop when shuffled\n(test split, SIMULATION)", fontsize=9)
        ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


def explain_model(name: str, entry: dict[str, Any], ds: SymptomDataset, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    spec = resolve_model(name, entry)
    if spec.kind not in SUPPORTED:
        raise ValueError(f"explanations support {SUPPORTED}, not {spec.kind!r}")
    inputs = build_inputs(ds)
    seed = int(config.get("model_seed", 0))
    model = fit_for_seed(spec, ds, inputs, seed, float(config.get("validation_fraction", 0.15)))
    x_all, names = tabular_matrix(inputs, spec.features)
    test_idx = np.flatnonzero(ds.split_mask("test"))
    x, y = x_all[test_idx], ds.syndrome_index[test_idx]
    contrib, bias, method = contributions(model, x)
    proba = model.heads["syndrome"].predict_proba(x)
    block, symptom = groups_of(names, "block"), groups_of(names, "symptom")
    n_repeats = int(config.get("n_repeats", 5))
    examples = pick_examples(ds, test_idx, inputs.n_observed)
    position = {int(i): k for k, i in enumerate(test_idx)}
    result = {
        "kind": spec.kind, "model_seed": seed, "method": method, "features": names, "n_test": int(len(test_idx)),
        "groups_block": {k: [names[i] for i in v] for k, v in block.items()},
        "global_feature": global_importance(contrib, {n: [i] for i, n in enumerate(names)}),
        "global_block": global_importance(contrib, block),
        "global_symptom": global_importance(contrib, symptom),
        "permutation_block": permutation_importance(model, x, y, block, n_repeats, seed),
        "permutation_symptom": permutation_importance(model, x, y, symptom, n_repeats, seed),
        "examples": individual(contrib, bias, proba, x, names, [position[i] for i in examples],
                               ds.patients["patient_id"].to_numpy()[test_idx], y),
        "additivity_max_error": additivity_error(model, x, contrib, bias, proba),
    }
    arrays = {"patient_id": ds.patients["patient_id"].to_numpy()[test_idx], "contributions": contrib,
              "bias": bias, "proba": proba, "feature_names": np.array(names), "class_labels": np.array(SYNDROMES)}
    return result, arrays


def additivity_error(model: TabularModel, x: np.ndarray, contrib: np.ndarray, bias: np.ndarray, proba: np.ndarray) -> float:
    """Max |bias + sum(contributions) - model output| (margin for XGBoost, probability for RF)."""
    total = bias + contrib.sum(axis=2)
    if model.spec.kind == "xgboost":
        head = model.heads["syndrome"]
        margin = head.model.predict(x, output_margin=True, iteration_range=(0, head.model.best_iteration + 1))
        if margin.ndim == 1:
            margin = np.stack([-margin, margin], axis=1)
        return float(np.abs(total[:, head.classes_] - margin).max())
    return float(np.abs(total - proba).max())


def run(config: dict[str, Any], overwrite: bool = False) -> Path:
    ds = load_dataset(config["dataset"])
    out = resolve(config["output_dir"])
    info = base_info(config | {"seeds": [config.get("model_seed", 0)]}, resolve(config["dataset"]), ds.meta)
    with RunRecorder(out, info, overwrite or bool(config.get("overwrite", False))) as recorder:
        results = {}
        for name, entry in config["models"].items():
            results[name], arrays = explain_model(name, entry or {}, ds, config)
            np.savez_compressed(out / f"contributions_{name}.npz", **arrays)
            pd.DataFrame([{"feature": k, **v} for k, v in results[name]["global_feature"].items()]).to_csv(
                out / f"global_feature_{name}.csv", index=False)
            pd.DataFrame([{"group": k, **v} for k, v in results[name]["permutation_block"].items()]).to_csv(
                out / f"permutation_block_{name}.csv", index=False)
            print(f"{name}: explained {results[name]['n_test']} test patients")
        (out / "explanations.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        recorder.info["plots"] = plot_groups(results, out / "permutation_block.png")
        (out / "report.md").write_text(render(results, recorder.info), encoding="utf-8")
    return out


def render(results: dict[str, Any], info: dict[str, Any]) -> str:
    parts = [f"# Phase 2 explanations (`{info['config']['name']}`)\n", HEADER, RESEARCH_ONLY, f"> {DISCLAIMER}\n",
             f"- dataset `{info['dataset']}`, commit `{info['git_commit']}`, run id `{info['run_id']}`; "
             "models fitted as in src/train.py; explanations on the test split.",
             "- Blocks: symptom_identity = present_*, timing = onset_*/since_*, presentation_delay, "
             "symptom_count = n_observed, context = hour/indoor/asleep.\n"]
    for name, res in results.items():
        perm = [{"group": k, "macro_f1_drop": f"{v['macro_f1_drop']:.4f} ± {v['macro_f1_drop_sd']:.4f}",
                 "nll_rise": f"{v['nll_rise']:.4f} ± {v['nll_rise_sd']:.4f}"}
                for k, v in sorted(res["permutation_block"].items(), key=lambda kv: -kv[1]["macro_f1_drop"])]
        sym = [{"symptom / group": k, "macro_f1_drop": f"{v['macro_f1_drop']:.4f}", "nll_rise": f"{v['nll_rise']:.4f}"}
               for k, v in sorted(res["permutation_symptom"].items(), key=lambda kv: -kv[1]["nll_rise"])[:12]]
        contrib = [{"group": k, "mean |contribution| (all classes)": f"{v['all_classes']:.4f}",
                    "toward non-venomous/dry": f"{v['non-venomous/dry']:.4f}"}
                   for k, v in res["global_block"].items()]
        parts += [f"## {name} ({res['method']})\n",
                  f"Additivity check (bias + contributions vs model output): max error {res['additivity_max_error']:.2e}.\n",
                  "### Permutation importance by block (test split)\n", table(perm),
                  "\n### Permutation importance by symptom (top 12 by NLL rise)\n", table(sym),
                  "\n### Mean absolute contribution by block\n", table(contrib),
                  "\n### Individual examples (top contributions toward the predicted class)\n"]
        for ex in res["examples"]:
            tops = "; ".join(f"{t['feature']}={t['value'] if t['value'] is not None else 'NaN'}: {t['contribution']:+.3f}"
                             for t in ex["top"][:5]) or "(no non-zero contribution)"
            parts.append(f"- patient {ex['patient_id']}: true {ex['true']}, predicted {ex['predicted']} "
                         f"(p={ex['p_predicted']:.2f}, P(envenomed)={ex['p_envenomed']:.2f}); {tops}")
        parts.append("")
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    print(f"wrote explanations to {run(config, overwrite=args.overwrite)}")


if __name__ == "__main__":
    main()
