"""Tests for stratified split assignment and split audits (src/data/splits.py)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.generate import generate
from src.data.simulator import assign_splits
from src.data.splits import (
    RARE,
    SplitLeakageError,
    allocate,
    assign_splits_stratified,
    check_disjoint,
    split_summary,
    strata_with_fallback,
)

FRACTIONS = {"train": 0.6, "calibration": 0.2, "test": 0.2}


def labels(n_a: int = 300, n_b: int = 200, n_rare: int = 7) -> tuple[list[str], list[str]]:
    species = ["a"] * n_a + ["b"] * n_b + ["a"] * n_rare
    syndrome = ["neurotoxic"] * n_a + ["non-venomous/dry"] * n_b + ["local-only"] * n_rare
    return species, syndrome


def test_allocate_sums_and_is_proportional() -> None:
    probs = np.array([0.6, 0.2, 0.2])
    for n in (0, 1, 7, 101, 1000):
        counts = allocate(n, probs)
        assert counts.sum() == n and (np.abs(counts - probs * n) < 1).all()


def test_stratified_preserves_class_mix_in_every_split() -> None:
    species, syndrome = labels()
    split, info = assign_splits_stratified(species, syndrome, FRACTIONS, seed=0, min_stratum=10)
    df = pd.DataFrame({"species": species, "venom_syndrome": syndrome, "split": split})
    for name, frac in FRACTIONS.items():
        rows = df[df["split"] == name]
        for cls, total in df["venom_syndrome"].value_counts().items():
            if total >= 10:
                assert abs((rows["venom_syndrome"] == cls).sum() - frac * total) < 1
    # the 7-patient local-only stratum is too small: logged fallback, then pooled
    assert info["joint_strata_fallen_back_to_syndrome"] == ["a|local-only"]
    assert info["syndrome_strata_pooled_as_rare"] == ["local-only"]
    assert info["strategy"] == "stratified"


def test_stratified_is_seeded_and_deterministic() -> None:
    species, syndrome = labels()
    a, _ = assign_splits_stratified(species, syndrome, FRACTIONS, seed=5)
    b, _ = assign_splits_stratified(species, syndrome, FRACTIONS, seed=5)
    c, _ = assign_splits_stratified(species, syndrome, FRACTIONS, seed=6)
    assert (a == b).all() and not (a == c).all()


def test_strata_fallback_levels() -> None:
    strata, info = strata_with_fallback(["a", "a", "b"], ["x", "x", "y"], min_stratum=2)
    assert list(strata) == ["a|x", "a|x", RARE]
    assert info["n_strata"] == 2


def test_bad_inputs() -> None:
    with pytest.raises(ValueError):
        assign_splits_stratified(["a"], ["x", "y"], FRACTIONS, 0)
    with pytest.raises(ValueError):
        assign_splits_stratified(["a"], ["x"], {"train": 0.5, "test": 0.6}, 0)
    with pytest.raises(ValueError):
        assign_splits_stratified(["a"], ["x"], FRACTIONS, 0, min_stratum=0)


def patients(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "patient_id": np.arange(n),
        "species": rng.choice(["a", "b"], n),
        "venom_syndrome": rng.choice(["neurotoxic", "non-venomous/dry"], n),
        "dry_bite": rng.random(n) < 0.1,
        "split": assign_splits(n, FRACTIONS, 0),
    })


def test_split_summary_counts_and_separation() -> None:
    df = patients()
    summary = split_summary(df, inputs_matrix=np.arange(len(df))[:, None].astype(float))
    assert sum(s["n"] for s in summary["splits"].values()) == len(df)
    for s in summary["splits"].values():
        assert sum(v["n"] for v in s["syndrome"].values()) == s["n"]
        assert "haemotoxic" in s["missing_classes"]
    assert summary["identical_inputs_to_train"] == {"calibration": 0, "test": 0}


def test_split_summary_detects_duplicates_and_identical_inputs() -> None:
    df = patients()
    x = np.zeros((len(df), 2))  # everyone presents identically
    summary = split_summary(df, inputs_matrix=x)
    assert summary["identical_inputs_to_train"]["test"] == (df["split"] == "test").sum()
    dup = pd.concat([df, df.iloc[[0]].assign(split="test")], ignore_index=True)
    with pytest.raises(SplitLeakageError):
        split_summary(dup)


def test_check_disjoint() -> None:
    a = np.array([True, False, False])
    check_disjoint({"a": a, "b": ~a})
    with pytest.raises(SplitLeakageError):
        check_disjoint({"a": a, "b": np.ones(3, bool)})


def test_generate_split_strategy(knowledge_dir: Path, tmp_path: Path) -> None:
    base = {"name": "t", "seed": 3, "n_patients": 400, "knowledge_dir": str(knowledge_dir)}
    random_out = generate({**base, "output_dir": str(tmp_path / "r")})
    strat_out = generate({**base, "output_dir": str(tmp_path / "s"), "split_strategy": "stratified",
                          "split_min_stratum": 10})
    r = pd.read_csv(random_out / "patients.csv")
    s = pd.read_csv(strat_out / "patients.csv")
    # default keeps the original random assignment exactly
    assert (r["split"].to_numpy() == assign_splits(400, FRACTIONS, 3)).all()
    # same patients either way; only the split column differs
    pd.testing.assert_frame_equal(r.drop(columns="split"), s.drop(columns="split"))
    meta = json.loads((strat_out / "meta.json").read_text())
    assert meta["split_assignment"]["strategy"] == "stratified"
    assert set(meta["split_summary"]["splits"]) == {"train", "calibration", "test"}
    with pytest.raises(ValueError):
        generate({**base, "output_dir": str(tmp_path / "x"), "split_strategy": "bogus"})
