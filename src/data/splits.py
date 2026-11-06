"""Split assignment (stratified option) and split audits. Works on SIMULATION data.

`assign_splits_stratified` keeps the class mix the same in every split. Strata are
`species|venom_syndrome` (so dry bites of venomous species stay represented); a stratum with
fewer than `min_stratum` patients falls back to its syndrome alone, and syndrome strata that are
still too small are pooled into one `rare` stratum. The fallbacks used are returned so they can be
logged. Within a stratum, counts follow the split fractions by largest remainder.

`split_summary` records sizes and class distributions per split and checks patient-level
separation: every patient id in exactly one split, and no test or calibration input identical
to a training input.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from src.data.simulator import SYNDROMES

DRY = SYNDROMES[-1]

STRATEGIES = ("random", "stratified")
RARE = "rare"


class SplitLeakageError(ValueError):
    """Raised when a patient or an identical input appears in more than one split."""


def check_fractions(fractions: dict[str, float]) -> tuple[list[str], np.ndarray]:
    names = list(fractions)
    probs = np.array([fractions[k] for k in names], dtype=float)
    if not names or not np.isfinite(probs).all() or (probs < 0).any() or not np.isclose(probs.sum(), 1.0):
        raise ValueError("split fractions must be finite, non-negative and sum to 1")
    return names, probs


def allocate(n: int, probs: np.ndarray) -> np.ndarray:
    """Integer counts summing to `n`, proportional to `probs` (largest remainder)."""
    raw = probs * n
    counts = np.floor(raw).astype(int)
    order = np.argsort(-(raw - counts), kind="stable")
    counts[order[: n - counts.sum()]] += 1
    return counts


def strata_with_fallback(
    species: Sequence[str], syndrome: Sequence[str], min_stratum: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Joint species|syndrome strata, falling back to syndrome, then to one `rare` pool."""
    joint = np.array([f"{a}|{b}" for a, b in zip(species, syndrome)], dtype=object)
    syn = np.asarray(syndrome, dtype=object)
    sizes = pd.Series(joint).value_counts()
    small_joint = sorted(sizes[sizes < min_stratum].index)
    strata = np.where(np.isin(joint, small_joint), syn, joint)
    sizes = pd.Series(strata).value_counts()
    small_syndrome = sorted(s for s in sizes[sizes < min_stratum].index if s in set(syn))
    strata = np.where(np.isin(strata, small_syndrome), RARE, strata)
    info = {
        "min_stratum": int(min_stratum),
        "joint_strata_fallen_back_to_syndrome": small_joint,
        "syndrome_strata_pooled_as_rare": small_syndrome,
        "n_strata": int(len(set(strata))),
    }
    return strata, info


def assign_splits_stratified(
    species: Sequence[str], syndrome: Sequence[str], fractions: dict[str, float], seed: int,
    min_stratum: int = 20,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Split labels stratified by species|syndrome with logged fallbacks (see module doc)."""
    if len(species) != len(syndrome):
        raise ValueError("species and syndrome must have the same length")
    if min_stratum < 1:
        raise ValueError("min_stratum must be >= 1")
    names, probs = check_fractions(fractions)
    strata, info = strata_with_fallback(species, syndrome, min_stratum)
    rng = np.random.default_rng([seed, 3])
    labels = np.empty(len(strata), dtype=object)
    for stratum in sorted(set(strata)):
        idx = rng.permutation(np.flatnonzero(strata == stratum))
        labels[idx] = np.repeat(np.array(names, dtype=object), allocate(len(idx), probs))
    return labels, {"strategy": "stratified", "seed": int(seed), **info}


def _distribution(values: pd.Series, labels: Sequence[str] | None = None) -> dict[str, dict[str, float]]:
    counts = values.value_counts()
    keys = list(labels) if labels is not None else sorted(counts.index)
    n = max(len(values), 1)
    return {k: {"n": int(counts.get(k, 0)), "share": round(float(counts.get(k, 0)) / n, 4)} for k in keys}


def split_summary(
    patients: pd.DataFrame, inputs_matrix: np.ndarray | None = None, train: str = "train",
) -> dict[str, Any]:
    """Sizes and syndrome / species / dry-envenomed distributions per split, plus separation checks.

    Raises SplitLeakageError if a patient id is repeated or appears in more than one split.
    `inputs_matrix` (one row per patient, the model's input features) is used to count held-out
    patients whose inputs are identical to some training patient's; this is reported, not an
    error, because two independent patients can present identically (e.g. nothing observed).
    """
    ids = patients["patient_id"]
    if ids.duplicated().any():
        raise SplitLeakageError("duplicated patient_id: a patient appears more than once")
    species_labels = sorted(patients["species"].unique())
    envenomed = patients["venom_syndrome"] != DRY
    out: dict[str, Any] = {"n_total": int(len(patients)), "splits": {}}
    for split, rows in patients.groupby("split", sort=True):
        env = envenomed[rows.index]
        out["splits"][str(split)] = {
            "n": int(len(rows)),
            "share": round(len(rows) / max(len(patients), 1), 4),
            "syndrome": _distribution(rows["venom_syndrome"], SYNDROMES),
            "species": _distribution(rows["species"], species_labels),
            "envenomed": {"n": int(env.sum()), "share": round(float(env.mean()), 4) if len(rows) else 0.0},
            "dry_bite": {"n": int(rows["dry_bite"].sum()), "share": round(float(rows["dry_bite"].mean()), 4)}
            if "dry_bite" in rows and len(rows) else None,
            "missing_classes": [s for s in SYNDROMES if (rows["venom_syndrome"] == s).sum() == 0],
        }
    out["patient_ids_unique"] = True  # checked above: each patient is in exactly one split
    if inputs_matrix is not None:
        if len(inputs_matrix) != len(patients):
            raise ValueError("inputs_matrix must have one row per patient")
        keys = [np.asarray(r, dtype=float).tobytes() for r in np.nan_to_num(inputs_matrix, nan=-9e9)]
        split = patients["split"].to_numpy()
        train_keys = {k for k, s in zip(keys, split) if s == train}
        out["identical_inputs_to_train"] = {
            str(name): sum(1 for k, s in zip(keys, split) if s == name and k in train_keys)
            for name in sorted(set(split)) if name != train
        }
    return out


def check_disjoint(masks: dict[str, np.ndarray]) -> None:
    """Raise SplitLeakageError if any two boolean index masks share a patient."""
    names = list(masks)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (masks[a] & masks[b]).any():
                raise SplitLeakageError(f"patients shared between {a!r} and {b!r}")
