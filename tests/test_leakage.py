"""Leakage tests: models may only see what is known at presentation.

Besides name checks, these tests perturb everything a model must NOT see (targets, simulator
diagnostics, placeholder columns, post-presentation and label-only events) in the raw files
and require every model input to stay bit-identical.
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.dataset import build_sequences, load_dataset
from src.data.features import (
    FORBIDDEN_COLUMNS,
    FeatureSpec,
    LeakageError,
    build_inputs,
    select_allowed,
    tabular_matrix,
    validate_feature_names,
)
from src.data.generate import generate
from src.models.registry import HEADS, fit_model, resolve_model
from src.models.symptom_transformer import collate
from tests.conftest import write_knowledge

SPECS = [
    FeatureSpec(),
    FeatureSpec(context=True),
    FeatureSpec(onset=False, elapsed=False),
    FeatureSpec(symptom_identity=False),
    FeatureSpec(presentation=False, elapsed=False),
    FeatureSpec(drop_groups=("local",)),
    FeatureSpec(symptoms=False, presentation=False, context=True),
]


@pytest.fixture(scope="module")
def sim_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("leak")
    knowledge = write_knowledge(root / "knowledge")
    return generate({
        "name": "leak", "seed": 11, "n_patients": 400, "knowledge_dir": str(knowledge),
        "output_dir": str(root / "sim"), "presentation_hours": [0.5, 4.0],
    })


def perturbed_copy(src: Path, dst: Path, seed: int = 0) -> Path:
    """Same dataset with every forbidden source of information scrambled."""
    shutil.copytree(src, dst)
    rng = np.random.default_rng(seed)
    patients = pd.read_csv(dst / "patients.csv")
    events = pd.read_csv(dst / "events.csv")
    n = len(patients)
    # Random values, not permutations: a permutation of a constant column changes nothing.
    patients["species"] = rng.choice(patients["species"].unique(), n)
    patients["venom_syndrome"] = rng.choice(["neurotoxic", "haemotoxic", "local-only", "non-venomous/dry"], n)
    patients["dry_bite"] = rng.random(n) < 0.5
    for col in ("order_violations", "n_assumed_onsets", "n_unknown_onsets"):
        patients[col] = rng.integers(0, 9, n)
    patients["lat"], patients["lon"], patients["month"] = rng.random(n), rng.random(n), rng.integers(1, 13, n)
    for col in [c for c in patients.columns if c.startswith("onset_")]:
        patients[col] = rng.random(n) * 100
    symptom = events["symptom"].iloc[0]
    extra = pd.DataFrame({
        "patient_id": np.repeat(patients["patient_id"].to_numpy(), 2),
        "symptom": symptom,
        # one event after presentation (not observed) and one label-only event per patient
        "hours": np.column_stack([patients["presentation_hours"] + 5.0, np.full(n, np.nan)]).ravel(),
        "observed": False,
        "onset_assumed": False,
        "onset_unknown": np.tile([False, True], n),
    })
    pd.concat([events, extra]).to_csv(dst / "events.csv", index=False)
    patients.to_csv(dst / "patients.csv", index=False)
    return dst


def test_select_allowed_rejects_every_forbidden_column() -> None:
    frame = pd.DataFrame({c: [0] for c in [*FORBIDDEN_COLUMNS, "onset_ptosis", "made_up", "presentation_hours"]})
    for col in [*FORBIDDEN_COLUMNS, "onset_ptosis", "made_up"]:
        with pytest.raises(LeakageError):
            select_allowed(frame, ["presentation_hours", col])
    assert list(select_allowed(frame, ["presentation_hours"]).columns) == ["presentation_hours"]


def test_injecting_a_forbidden_column_is_rejected(sim_dir: Path) -> None:
    ds = load_dataset(sim_dir)
    for col in ("dry_bite", "venom_syndrome", "species", "n_unknown_onsets", "split"):
        with pytest.raises(LeakageError):
            build_inputs(ds, context_columns=["hour_of_day", col])
    x, names = tabular_matrix(build_inputs(ds))
    with pytest.raises(LeakageError):
        validate_feature_names([*names, "venom_syndrome"], ds.symptoms)
    with pytest.raises(LeakageError):
        validate_feature_names([*names, "species_index"], ds.symptoms)
    with pytest.raises(LeakageError):
        validate_feature_names([*names, names[0]], ds.symptoms)  # duplicates hide injected columns


def test_extra_patient_columns_never_reach_features(sim_dir: Path) -> None:
    ds = load_dataset(sim_dir)
    before = tabular_matrix(build_inputs(ds), FeatureSpec(context=True))
    ds.patients["leak"] = ds.syndrome_index  # a target copy under an innocent name
    after = tabular_matrix(build_inputs(ds), FeatureSpec(context=True))
    assert before[1] == after[1]
    np.testing.assert_array_equal(before[0], after[0])


def test_model_inputs_invariant_to_targets_diagnostics_and_hidden_events(sim_dir: Path, tmp_path: Path) -> None:
    clean = load_dataset(sim_dir)
    dirty = load_dataset(perturbed_copy(sim_dir, tmp_path / "dirty"))
    for col in ("species", "venom_syndrome", "dry_bite", "n_unknown_onsets"):  # the perturbation did something
        assert (clean.patients[col].to_numpy() != dirty.patients[col].to_numpy()).any(), col
    a, b = build_inputs(clean), build_inputs(dirty)
    assert len(a.sequences) == len(b.sequences)
    for s, t in zip(a.sequences, b.sequences):
        np.testing.assert_array_equal(s, t)
    np.testing.assert_array_equal(a.presentation, b.presentation)
    pd.testing.assert_frame_equal(a.context, b.context)
    for spec in SPECS:
        xa, na = tabular_matrix(a, spec)
        xb, nb = tabular_matrix(b, spec)
        assert na == nb
        np.testing.assert_array_equal(xa, xb)
    for ta, tb in zip(collate(list(a.sequences), a.presentation), collate(list(b.sequences), b.presentation)):
        assert (ta == tb).all()  # transformer tensors


def test_post_presentation_and_label_only_events_are_excluded(sim_dir: Path) -> None:
    ds = load_dataset(sim_dir)
    events = pd.read_csv(sim_dir / "events.csv")
    hidden = events[~events["observed"] | events["onset_unknown"]]
    assert len(hidden)  # the fixture has hidden events to exclude
    for seq, presentation in zip(ds.sequences, ds.patients["presentation_hours"]):
        assert (seq[:, 1] <= presentation + 1e-9).all()
        assert np.isfinite(seq[:, 1]).all()
    n_visible = sum(len(s) for s in ds.sequences)
    assert n_visible == int((events["observed"] & ~events["onset_unknown"]).sum())


def test_mislabelled_future_event_is_refused() -> None:
    events = pd.DataFrame({"patient_id": [0], "symptom": ["a"], "hours": [5.0], "observed": [True],
                           "onset_assumed": [False], "onset_unknown": [False]})
    with pytest.raises(ValueError, match="after presentation"):
        build_sequences(events, 1, ("a",), presentation=np.array([2.0]))


def test_every_model_feature_name_is_allowlisted(sim_dir: Path) -> None:
    ds = load_dataset(sim_dir)
    inputs = build_inputs(ds)
    for spec in SPECS:
        _, names = tabular_matrix(inputs, spec)
        validate_feature_names(names, ds.symptoms)
        assert not any(c in name for name in names for c in ("species", "syndrome", "dry_bite", "unknown"))


def _fit_predict(kind: str, ds, y_syn, y_sp, params=None):
    spec = resolve_model(kind, {"params": params or {}} if kind != "transformer" else (params or {}))
    train = np.flatnonzero(ds.split_mask("train"))
    model = fit_model(spec, build_inputs(ds), y_syn, y_sp, train[:200], train[200:], 0, len(ds.species))
    return model.predict(build_inputs(ds))


@pytest.mark.parametrize("kind,params", [
    ("xgboost", {"n_estimators": 20, "early_stopping_rounds": 5}),
    ("logistic_regression", {}),
    ("random_forest", {"n_estimators": 20}),
])
def test_each_label_only_trains_its_own_head(sim_dir: Path, kind: str, params: dict) -> None:
    ds = load_dataset(sim_dir)
    rng = np.random.default_rng(3)
    y_syn, y_sp = ds.syndrome_index, ds.species_index
    base = _fit_predict(kind, ds, y_syn, y_sp, params)
    shuffled_species = _fit_predict(kind, ds, y_syn, rng.permutation(y_sp), params)
    np.testing.assert_allclose(base.p_syndrome, shuffled_species.p_syndrome)
    shuffled_syndrome = _fit_predict(kind, ds, rng.permutation(y_syn), y_sp, params)
    np.testing.assert_allclose(base.p_species, shuffled_syndrome.p_species)


def test_transformer_species_labels_act_only_through_species_loss(sim_dir: Path) -> None:
    """With the species loss switched off, species labels cannot affect the syndrome head."""
    ds = load_dataset(sim_dir)
    params = {"d_model": 16, "n_heads": 2, "n_layers": 1, "max_epochs": 2, "batch_size": 64,
              "species_loss_weight": 0.0, "dropout": 0.0}
    a = _fit_predict("transformer", ds, ds.syndrome_index, ds.species_index, params)
    b = _fit_predict("transformer", ds, ds.syndrome_index, np.random.default_rng(1).permutation(ds.species_index), params)
    np.testing.assert_allclose(a.p_syndrome, b.p_syndrome, atol=1e-6)
    assert resolve_model("transformer", {}).heads == HEADS


def test_train_run_records_and_validates_every_models_inputs(sim_dir: Path, tmp_path: Path) -> None:
    from src.train import run

    config = {
        "name": "leak", "dataset": str(sim_dir), "output_dir": str(tmp_path / "run"), "seeds": [0],
        "torch_threads": 1,
        "models": {
            "prior": {}, "rule": {},
            "xgboost": {"params": {"n_estimators": 10, "early_stopping_rounds": 3}},
            "xgboost_context": {"params": {"n_estimators": 10, "early_stopping_rounds": 3}},
            "logistic_regression": {}, "random_forest": {"params": {"n_estimators": 10}},
            "transformer": {"d_model": 16, "n_heads": 2, "n_layers": 1, "max_epochs": 1},
        },
    }
    run(config)
    info = json.loads((tmp_path / "run" / "run.json").read_text())
    ds = load_dataset(sim_dir)
    for name in ("xgboost", "xgboost_context", "logistic_regression", "random_forest"):
        validate_feature_names(info["model_inputs"][name], ds.symptoms)
    assert "hour_sin" in info["model_inputs"]["xgboost_context"]
    assert "hour_sin" not in info["model_inputs"]["xgboost"]
