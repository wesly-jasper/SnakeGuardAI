"""Post-hoc probability calibration, fitted on the calibration split only. SIMULATION use.

Methods, for the multiclass venom-syndrome output and for the binary P(envenomed):
- `temperature`: one scale on log-probabilities (binary: on the logit), fitted by NLL.
- `sigmoid`: Platt scaling. Binary: logistic regression on the logit. Multiclass: one-vs-rest
  Platt per class, then renormalised.
- `isotonic`: isotonic regression (one-vs-rest and renormalised for multiclass). Only fitted
  when the calibration split is large enough (`min_isotonic_n` patients and
  `min_isotonic_class` positives and negatives per class); otherwise skipped with a reason.

Raw probabilities are kept; calibrated ones are additional outputs. `evaluate_calibration`
fits on the calibration rows and reports NLL, Brier and ECE for raw and calibrated
probabilities on the evaluation rows, and whether calibration helped (lower NLL).
Calibrators never see evaluation labels (`fit_*` only receive calibration arrays).
Not a clinical tool; calibrated probabilities on simulated data are SIMULATION results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from src.evaluate import DRY_INDEX, brier_score, expected_calibration_error, negative_log_likelihood

METHODS = ("temperature", "sigmoid", "isotonic")
EPS = 1e-12
N_BINS = 15
MIN_ISOTONIC_N = 1000
MIN_ISOTONIC_CLASS = 50


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return np.log(p) - np.log1p(-p)


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _normalise(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, None)
    return p / p.sum(axis=1, keepdims=True)


@dataclass
class Calibrator:
    """A fitted calibrator. `kind` is `multiclass` or `binary`; `params` is JSON-serialisable."""

    method: str
    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    models: list[Any] = field(default_factory=list, repr=False)

    def apply(self, p: np.ndarray) -> np.ndarray:
        p = np.asarray(p, dtype=float)
        if self.kind == "binary":
            return self._apply_binary(p)
        if self.method == "temperature":
            return _softmax(np.log(np.clip(p, EPS, 1.0)) / self.params["temperature"])
        cols = [self._apply_binary(p[:, k], self.models[k]) for k in range(p.shape[1])]
        return _normalise(np.column_stack(cols))

    def _apply_binary(self, p: np.ndarray, model: Any = None) -> np.ndarray:
        if self.method == "temperature":
            return 1.0 / (1.0 + np.exp(-_logit(p) / self.params["temperature"]))
        model = self.models[0] if model is None else model
        if self.method == "sigmoid":
            if model is None:
                return p
            return model.predict_proba(_logit(p)[:, None])[:, 1]
        return np.clip(model.predict(p), 0.0, 1.0)


def _fit_platt(p: np.ndarray, y: np.ndarray) -> tuple[LogisticRegression | None, dict[str, Any]]:
    """Platt scaling; with only one label present it is not identifiable and is left as identity."""
    if len(np.unique(y)) < 2:
        return None, {"a": None, "b": None, "identity_single_class": True}
    model = LogisticRegression(C=1e6, max_iter=1000).fit(_logit(p)[:, None], y)
    return model, {"a": float(model.coef_[0, 0]), "b": float(model.intercept_[0])}


def _fit_isotonic(p: np.ndarray, y: np.ndarray) -> IsotonicRegression:
    return IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p, y)


def isotonic_supported(y: np.ndarray, n_classes: int, min_n: int = MIN_ISOTONIC_N,
                       min_class: int = MIN_ISOTONIC_CLASS) -> tuple[bool, str]:
    """Whether the calibration sample is large enough for isotonic regression."""
    if len(y) < min_n:
        return False, f"calibration n={len(y)} < {min_n}"
    counts = np.bincount(y, minlength=n_classes)
    small = [int(c) for c in range(n_classes) if min(counts[c], len(y) - counts[c]) < min_class]
    if small:
        return False, f"classes {small} have fewer than {min_class} positives or negatives"
    return True, ""


def fit_multiclass(method: str, p: np.ndarray, y: np.ndarray) -> Calibrator:
    """Fit a multiclass calibrator on calibration-split probabilities `p` and labels `y`."""
    p, y = np.asarray(p, dtype=float), np.asarray(y, dtype=int)
    if method == "temperature":
        logp = np.log(np.clip(p, EPS, 1.0))

        def nll(log_t: float) -> float:
            return negative_log_likelihood(_softmax(logp / np.exp(log_t)), y)

        res = minimize_scalar(nll, bounds=(-3.0, 3.0), method="bounded")
        return Calibrator(method, "multiclass", {"temperature": float(np.exp(res.x))})
    if method == "sigmoid":
        fitted = [_fit_platt(p[:, k], (y == k).astype(int)) for k in range(p.shape[1])]
        return Calibrator(method, "multiclass", {"per_class": [f[1] for f in fitted]}, [f[0] for f in fitted])
    if method == "isotonic":
        models = [_fit_isotonic(p[:, k], (y == k).astype(float)) for k in range(p.shape[1])]
        return Calibrator(method, "multiclass", {"n_thresholds": [int(len(m.X_thresholds_)) for m in models]}, models)
    raise ValueError(f"unknown calibration method {method!r}; expected one of {METHODS}")


def fit_binary(method: str, p: np.ndarray, y: np.ndarray) -> Calibrator:
    """Fit a calibrator for a binary probability `p` (e.g. P(envenomed)) with 0/1 labels `y`."""
    p, y = np.asarray(p, dtype=float), np.asarray(y, dtype=int)
    if method == "temperature":
        z = _logit(p)

        def nll(log_t: float) -> float:
            q = np.clip(1.0 / (1.0 + np.exp(-z / np.exp(log_t))), EPS, 1 - EPS)
            return float(-(y * np.log(q) + (1 - y) * np.log(1 - q)).mean())

        res = minimize_scalar(nll, bounds=(-3.0, 3.0), method="bounded")
        return Calibrator(method, "binary", {"temperature": float(np.exp(res.x))})
    if method == "sigmoid":
        model, params = _fit_platt(p, y)
        return Calibrator(method, "binary", params, [model])
    if method == "isotonic":
        model = _fit_isotonic(p, y.astype(float))
        return Calibrator(method, "binary", {"n_thresholds": int(len(model.X_thresholds_))}, [model])
    raise ValueError(f"unknown calibration method {method!r}; expected one of {METHODS}")


def binary_metrics(p: np.ndarray, y: np.ndarray, n_bins: int = N_BINS) -> dict[str, float]:
    """NLL, Brier and ECE (equal-width bins on p) for a binary probability."""
    p, y = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS), np.asarray(y, dtype=int)
    if not len(y):
        return {"nll": float("nan"), "brier": float("nan"), "ece": float("nan")}
    bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    ece = sum(float((bins == b).mean()) * abs(float(y[bins == b].mean()) - float(p[bins == b].mean()))
              for b in range(n_bins) if (bins == b).any())
    return {
        "nll": float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
        "brier": float(((p - y) ** 2).mean()),
        "ece": float(ece),
    }


def multiclass_metrics(p: np.ndarray, y: np.ndarray) -> dict[str, float]:
    if not len(y):
        return {"nll": float("nan"), "brier": float("nan"), "ece": float("nan")}
    return {"nll": negative_log_likelihood(p, y), "brier": brier_score(p, y), "ece": expected_calibration_error(p, y)}


def reliability_table(p: np.ndarray, y: np.ndarray, n_bins: int = 10) -> list[dict[str, float]]:
    """Per-bin mean predicted probability, observed frequency and count (binary)."""
    p, y = np.asarray(p, dtype=float), np.asarray(y, dtype=int)
    bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    return [
        {"bin_low": b / n_bins, "bin_high": (b + 1) / n_bins, "n": int((bins == b).sum()),
         "mean_predicted": float(p[bins == b].mean()), "observed": float(y[bins == b].mean())}
        for b in range(n_bins) if (bins == b).any()
    ]


def envenomed_labels(y_syndrome: np.ndarray, dry_index: int = DRY_INDEX) -> np.ndarray:
    return (np.asarray(y_syndrome) != dry_index).astype(int)


def evaluate_calibration(
    p_syndrome: np.ndarray, y_syndrome: np.ndarray, fit_mask: np.ndarray, eval_mask: np.ndarray,
    methods: tuple[str, ...] = METHODS, min_isotonic_n: int = MIN_ISOTONIC_N,
    min_isotonic_class: int = MIN_ISOTONIC_CLASS,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Fit every method on `fit_mask` rows, evaluate raw and calibrated on `eval_mask` rows.

    Returns (report, arrays). `arrays` holds calibrated probabilities for all rows
    (`p_syndrome_<method>`, `p_envenomed_<method>`) plus `p_envenomed_raw`.
    """
    fit_mask, eval_mask = np.asarray(fit_mask, bool), np.asarray(eval_mask, bool)
    if (fit_mask & eval_mask).any():
        raise ValueError("calibration rows and evaluation rows overlap")
    p = np.asarray(p_syndrome, dtype=float)
    y = np.asarray(y_syndrome, dtype=int)
    y_env = envenomed_labels(y)
    p_env = 1.0 - p[:, DRY_INDEX]
    y_fit, y_eval = y[fit_mask], y[eval_mask]
    report: dict[str, Any] = {
        "fitted_on": "calibration split", "n_fit": int(fit_mask.sum()), "n_eval": int(eval_mask.sum()),
        "syndrome": {"raw": multiclass_metrics(p[eval_mask], y_eval)},
        "envenomed": {"raw": binary_metrics(p_env[eval_mask], y_env[eval_mask])},
        "reliability_envenomed": {"raw": reliability_table(p_env[eval_mask], y_env[eval_mask])},
        "methods": {}, "skipped": {},
    }
    arrays: dict[str, np.ndarray] = {"p_envenomed_raw": p_env}
    for method in methods:
        if method == "isotonic":
            ok, reason = isotonic_supported(y_fit, p.shape[1], min_isotonic_n, min_isotonic_class)
            if not ok:
                report["skipped"][method] = reason
                continue
        multi = fit_multiclass(method, p[fit_mask], y_fit)
        binary = fit_binary(method, p_env[fit_mask], y_env[fit_mask])
        p_cal, env_cal = multi.apply(p), binary.apply(p_env)
        arrays[f"p_syndrome_{method}"] = p_cal
        arrays[f"p_envenomed_{method}"] = env_cal
        syn = multiclass_metrics(p_cal[eval_mask], y_eval)
        env = binary_metrics(env_cal[eval_mask], y_env[eval_mask])
        report["syndrome"][method] = syn | {"helps_nll": syn["nll"] < report["syndrome"]["raw"]["nll"]}
        report["envenomed"][method] = env | {"helps_nll": env["nll"] < report["envenomed"]["raw"]["nll"]}
        report["reliability_envenomed"][method] = reliability_table(env_cal[eval_mask], y_env[eval_mask])
        report["methods"][method] = {"syndrome": multi.params, "envenomed": binary.params}
    return report, arrays


def plot_reliability(report: dict[str, Any], path: Any, title: str) -> bool:
    """Reliability diagram for P(envenomed); returns False if matplotlib is not installed."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot([0, 1], [0, 1], color="#999999", linewidth=1, linestyle="--", label="perfect")
    for name, rows in report["reliability_envenomed"].items():
        ax.plot([r["mean_predicted"] for r in rows], [r["observed"] for r in rows], marker="o", markersize=3,
                linewidth=1.5, label=name)
    ax.set_xlabel("predicted P(envenomed)")
    ax.set_ylabel("observed share envenomed")
    ax.set_title(title + "\n(SIMULATION)", fontsize=9)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True
