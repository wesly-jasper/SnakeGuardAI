"""Diagnostics for the copula + onset-order interaction (SIMULATION checks).

For every species, draws courses with the dataset's settings and compares each symptom's
onset distribution before ordering (first copula draw) and after ordering (push + redraws):

- marginals: n present, mean onset before/after, two-sample KS statistic before vs after,
  share of onsets changed by ordering, and a KS test of the pre-order onsets over all draws
  against Uniform(window), which the copula construction guarantees.
- pairs: each order rule's window status (compatible / partial / incompatible), how often
  both signs occur, violations left by the push alone and violations left after redraws.

Called by src/data/generate.py, which writes onset_diagnostics.md next to the dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.data.simulator import (
    CourseDraw,
    SpeciesSpec,
    apply_order,
    count_order_violations,
    draw_course,
    order_window_status,
)


def species_diagnostics(
    spec: SpeciesSpec, n: int, rng: np.random.Generator, severity_correlation: float, max_order_tries: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(marginal rows, pair rows) for one species from `n` simulated courses."""
    k = len(spec.symptoms)
    draws = [draw_course(spec, rng, severity_correlation, max_order_tries) for _ in range(n)]
    envenomed = [d for d in draws if not d.dry]
    raw_all = np.array([d.raw_onsets for d in draws]).reshape(n, k)
    marginals = []
    for j, symptom in enumerate(spec.symptoms):
        lo, hi = float(spec.onset_min[j]), float(spec.onset_max[j])
        before = np.array([d.raw_onsets[j] for d in envenomed if d.present[j]])
        after = np.array([d.onsets[j] for d in envenomed if d.present[j]])
        uniform_p = (
            float(stats.kstest(raw_all[:, j], "uniform", args=(lo, hi - lo)).pvalue) if hi > lo else np.nan
        )
        two_sample = stats.ks_2samp(before, after) if len(before) > 1 else None
        marginals.append({
            "species": spec.species, "symptom": symptom, "window": f"{lo:g}-{hi:g}",
            "onset_assumed": bool(spec.onset_assumed[j]) if spec.onset_assumed is not None else False,
            "n_present": len(before),
            "mean_before_order": float(before.mean()) if len(before) else np.nan,
            "mean_after_order": float(after.mean()) if len(after) else np.nan,
            "ks_before_vs_after": float(two_sample.statistic) if two_sample else np.nan,
            "share_changed": float(np.mean(np.abs(after - before) > 1e-9)) if len(before) else np.nan,
            "raw_vs_uniform_p": uniform_p,
        })
    pairs = []
    for rule, (b, a) in zip(order_window_status(spec), spec.order):
        both = [d for d in envenomed if d.present[b] and d.present[a]]
        pushed_only = [
            count_order_violations(_push(spec, d), d.present, ((b, a),)) for d in both
        ]
        final = [count_order_violations(d.onsets, d.present, ((b, a),)) for d in both]
        pairs.append({
            **{key: rule[key] for key in ("species", "before", "after", "status")},
            "before_window": "{:g}-{:g}".format(*rule["before_window"]),
            "after_window": "{:g}-{:g}".format(*rule["after_window"]),
            "n_both_present": len(both),
            "violations_after_push_only": int(sum(pushed_only)),
            "violations_after_redraws": int(sum(final)),
            "mean_redraws": float(np.mean([d.order_redraws for d in both])) if both else 0.0,
        })
    return pd.DataFrame(marginals), pd.DataFrame(pairs)


def _push(spec: SpeciesSpec, draw: CourseDraw) -> np.ndarray:
    """The first draw ordered by the push alone, without redraws."""
    return apply_order(draw.raw_onsets, draw.present, spec.onset_max, spec.order)


def onset_diagnostics(
    specs: dict[str, SpeciesSpec], n_per_species: int, seed: int, severity_correlation: float,
    max_order_tries: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Marginal and pair diagnostics for every species with symptoms."""
    rng = np.random.default_rng([seed, 2])
    parts = [
        species_diagnostics(spec, n_per_species, rng, severity_correlation, max_order_tries)
        for spec in specs.values() if spec.symptoms
    ]
    marginals = pd.concat([m for m, _ in parts], ignore_index=True) if parts else pd.DataFrame()
    pairs = pd.concat([p for _, p in parts if not p.empty], ignore_index=True) if any(
        not p.empty for _, p in parts) else pd.DataFrame()
    return marginals, pairs


def summarise(marginals: pd.DataFrame, pairs: pd.DataFrame) -> dict[str, object]:
    """Headline numbers for meta.json."""
    status = pairs["status"].value_counts().to_dict() if len(pairs) else {}
    return {
        "order_rules_by_status": status,
        "order_violations_after_push_only": int(pairs["violations_after_push_only"].sum()) if len(pairs) else 0,
        "order_violations_after_redraws": int(pairs["violations_after_redraws"].sum()) if len(pairs) else 0,
        "max_ks_before_vs_after_order": float(marginals["ks_before_vs_after"].max()) if len(marginals) else 0.0,
        "min_raw_vs_uniform_p": float(marginals["raw_vs_uniform_p"].min()) if len(marginals) else 1.0,
    }


def render(marginals: pd.DataFrame, pairs: pd.DataFrame, n_per_species: int) -> str:
    parts = [
        "# Onset diagnostics: copula and onset order",
        "",
        "> **SIMULATION CHECK.** Generated by src/data/diagnostics.py, "
        f"{n_per_species} courses per species.",
        "",
        "## Onset order rules",
        "",
        "`partial` rules cannot always be met by pushing the later sign; those courses are redrawn.",
        "Any violation left after redraws is flagged on the patient (`order_violations`).",
        "",
        pairs.to_markdown(index=False, floatfmt=".3f") if len(pairs) else "No order rules apply.",
        "",
        "## Onset marginals before and after ordering",
        "",
        "`raw_vs_uniform_p`: KS test of pre-order onsets (all draws) against Uniform(window);",
        "`ks_before_vs_after`: how far ordering moved each symptom's onset distribution",
        "(among patients who have it). `onset_assumed` rows use the fallback window (assumption).",
        "",
        marginals.to_markdown(index=False, floatfmt=".3f") if len(marginals) else "No symptoms.",
        "",
    ]
    return "\n".join(parts)
