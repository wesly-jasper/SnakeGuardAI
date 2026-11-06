"""Tests for src/data/dataset.py (model input built from observed events only)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.dataset import (
    build_sequences,
    context_features,
    load_dataset,
    observed_events,
    tabular_features,
    validation_split,
)
from src.data.generate import generate

SYMPTOMS = ("a", "b", "c")


def events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            (0, "b", 2.0, True, False, False),
            (0, "a", 1.0, True, False, False),
            (0, "c", 9.0, False, False, False),   # after presentation
            (2, "c", np.nan, False, False, True),  # label-only, onset unknown
            (2, "a", 0.5, True, False, False),
        ],
        columns=["patient_id", "symptom", "hours", "observed", "onset_assumed", "onset_unknown"],
    )


def test_observed_events_drop_unobserved_and_label_only() -> None:
    seen = observed_events(events())
    assert list(zip(seen["patient_id"], seen["symptom"])) == [(0, "b"), (0, "a"), (2, "a")]


def test_build_sequences_sorted_by_onset_with_empty_patients() -> None:
    seqs = build_sequences(events(), 3, SYMPTOMS)
    np.testing.assert_array_equal(seqs[0], [[0, 1.0], [1, 2.0]])
    assert seqs[1].shape == (0, 2)
    np.testing.assert_array_equal(seqs[2], [[0, 0.5]])


def test_build_sequences_rejects_unknown_symptom() -> None:
    with pytest.raises(ValueError, match="vocabulary"):
        build_sequences(events(), 3, ("b", "c"))


def test_context_features_handle_missing() -> None:
    patients = pd.DataFrame({"hour_of_day": [6.0, None], "indoor": [True, None], "asleep": ["False", "True"]})
    x = context_features(patients)
    np.testing.assert_allclose(x[0, :3], [1.0, 0.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(x[1, :3], [0.0, 0.0, 1.0])
    assert x[0, 3] == 1.0 and np.isnan(x[1, 3])
    np.testing.assert_array_equal(x[:, 4], [0.0, 1.0])


def test_validation_split_is_disjoint_subset_of_train() -> None:
    train = np.array([True] * 80 + [False] * 20)
    fit, val = validation_split(train, 0.25, seed=3)
    assert val.sum() == 20 and fit.sum() == 60
    assert not (fit & val).any() and not (val & ~train).any()
    again = validation_split(train, 0.25, seed=3)[1]
    np.testing.assert_array_equal(val, again)
    with pytest.raises(ValueError):
        validation_split(train, 1.0, seed=3)


@pytest.fixture
def dataset_dir(knowledge_dir: Path, tmp_path: Path) -> Path:
    return generate({
        "name": "t", "seed": 5, "n_patients": 300, "knowledge_dir": str(knowledge_dir),
        "output_dir": str(tmp_path / "sim"), "presentation_hours": [0.5, 4.0],
    })


def test_load_dataset_matches_observed_onsets(dataset_dir: Path) -> None:
    ds = load_dataset(dataset_dir)
    assert len(ds.sequences) == len(ds.patients) == 300
    for i, seq in enumerate(ds.sequences):
        row = ds.patients.iloc[i]
        assert (seq[:, 1] <= row["presentation_hours"] + 1e-9).all()
        observed = {ds.symptoms[int(k)]: h for k, h in seq}
        for symptom in ds.symptoms:
            col = f"onset_{symptom}"
            value = row[col] if col in row.index else np.nan
            if symptom in observed:
                assert value == pytest.approx(observed[symptom])
            else:
                assert np.isnan(value)


def test_tabular_features_shapes_and_values(dataset_dir: Path) -> None:
    ds = load_dataset(dataset_dir)
    x, names = tabular_features(ds)
    k = len(ds.symptoms)
    assert x.shape == (300, 3 * k + 2) and len(names) == x.shape[1]
    present = x[:, :k]
    np.testing.assert_array_equal(present.sum(1), [len(s) for s in ds.sequences])
    np.testing.assert_array_equal(np.isnan(x[:, k:2 * k]), present == 0)
    assert (x[:, 2 * k:3 * k][present == 1] >= -1e-9).all()  # time since onset is never negative
    x_ctx, names_ctx = tabular_features(ds, use_context=True)
    assert x_ctx.shape[1] == x.shape[1] + 5 and names_ctx[-1] == "asleep"
