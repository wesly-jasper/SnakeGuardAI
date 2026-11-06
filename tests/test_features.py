"""Tests for FeatureSpec switches in src/data/features.py (ablation inputs)."""

import numpy as np
import pandas as pd
import pytest

from src.data.features import FeatureSpec, ModelInputs, apply_spec, tabular_matrix

SYMPTOMS = ("pain", "ptosis", "bleed")
MARKERS = {"pain": "local", "ptosis": "neurotoxic", "bleed": "haemotoxic"}


def inputs() -> ModelInputs:
    return ModelInputs(
        sequences=(np.array([[0, 0.5], [1, 2.0]]), np.zeros((0, 2)), np.array([[2, 1.0]])),
        presentation=np.array([3.0, 1.0, 4.0]),
        context=pd.DataFrame({"hour_of_day": [6.0, None, 18.0], "indoor": [True, False, None],
                              "asleep": [False, False, True]}),
        symptoms=SYMPTOMS,
        markers=MARKERS,
    )


def test_full_spec_columns_and_values() -> None:
    x, names = tabular_matrix(inputs())
    assert names[:3] == ["present_pain", "present_ptosis", "present_bleed"]
    assert names[-2:] == ["presentation_hours", "n_observed"]
    np.testing.assert_array_equal(x[0, :3], [1, 1, 0])
    assert x[0, names.index("since_pain")] == 2.5
    assert np.isnan(x[1, names.index("onset_pain")])
    np.testing.assert_array_equal(x[:, -1], [2, 0, 1])


def test_presence_only_has_no_time_features() -> None:
    _, names = tabular_matrix(inputs(), FeatureSpec(onset=False, elapsed=False))
    assert not any(n.startswith(("onset_", "since_")) for n in names)
    assert "presentation_hours" in names


def test_temporal_only_has_no_symptom_identity() -> None:
    x, names = tabular_matrix(inputs(), FeatureSpec(symptom_identity=False, max_events=2))
    assert names == ["event0_onset", "event1_onset", "event0_since", "event1_since", "presentation_hours", "n_observed"]
    assert not any(s in n for n in names for s in SYMPTOMS)
    np.testing.assert_array_equal(x[0, :2], [0.5, 2.0])
    assert np.isnan(x[2, 1]) and x[2, 0] == 1.0
    # identity is really gone: swapping which symptom an event is gives the same row
    swapped = ModelInputs((np.array([[2, 0.5], [0, 2.0]]),) + inputs().sequences[1:], inputs().presentation,
                          inputs().context, SYMPTOMS, MARKERS)
    np.testing.assert_array_equal(tabular_matrix(swapped, FeatureSpec(symptom_identity=False, max_events=2))[0], x)


def test_no_presentation_removes_presentation_and_elapsed() -> None:
    x, names = tabular_matrix(inputs(), FeatureSpec(presentation=False, elapsed=False))
    assert "presentation_hours" not in names and not any(n.startswith("since_") for n in names)
    with pytest.raises(ValueError, match="reveals the presentation"):
        tabular_matrix(inputs(), FeatureSpec(presentation=False))


def test_drop_symptom_and_groups() -> None:
    dropped = apply_spec(inputs(), FeatureSpec(drop_symptoms=("ptosis",)))
    np.testing.assert_array_equal(dropped.sequences[0], [[0, 0.5]])
    x, names = tabular_matrix(inputs(), FeatureSpec(drop_groups=("local",)))
    assert x[0, names.index("present_pain")] == 0 and x[0, names.index("n_observed")] == 1
    x, names = tabular_matrix(inputs(), FeatureSpec(drop_groups=("systemic",)))
    assert x[:, names.index("n_observed")].tolist() == [1, 0, 0]
    with pytest.raises(ValueError):
        tabular_matrix(inputs(), FeatureSpec(drop_symptoms=("unknown",)))
    with pytest.raises(ValueError):
        tabular_matrix(inputs(), FeatureSpec(drop_groups=("cardiac",)))


def test_context_only() -> None:
    x, names = tabular_matrix(inputs(), FeatureSpec(symptoms=False, presentation=False, context=True))
    assert names == ["hour_sin", "hour_cos", "hour_missing", "indoor", "asleep"]
    np.testing.assert_allclose(x[0, :3], [1.0, 0.0, 0.0], atol=1e-12)
    assert x[1, 2] == 1.0 and np.isnan(x[2, 3])


def test_empty_spec_and_bad_options_rejected() -> None:
    with pytest.raises(ValueError):
        tabular_matrix(inputs(), FeatureSpec(symptoms=False, presentation=False))
    with pytest.raises(ValueError):
        FeatureSpec.from_dict({"bogus": 1})
    with pytest.raises(ValueError):
        tabular_matrix(inputs(), FeatureSpec(presence=False, onset=False, elapsed=False))
