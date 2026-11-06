"""Tests for the Phase 2 models: symptom transformer, trainer and XGBoost head."""

import numpy as np
import torch

from src.models.symptom_transformer import SymptomTransformer, TimeEncoding, collate
from src.models.trainer import fit_transformer, predict_proba
from src.models.xgb_baseline import XGBHead


def model() -> SymptomTransformer:
    torch.manual_seed(0)
    m = SymptomTransformer(n_symptoms=5, n_syndromes=4, n_species=3, d_model=16, n_heads=2, n_layers=1, dropout=0.0)
    return m.eval()


def test_time_encoding_shape() -> None:
    assert TimeEncoding(8)(torch.tensor([[0.0, 1.0, 48.0]])).shape == (1, 3, 8)


def test_collate_pads_and_allows_empty() -> None:
    seqs = [np.array([[1, 0.5], [3, 2.0]]), np.zeros((0, 2))]
    symptom, onset, padding, presentation = collate(seqs, np.array([3.0, 1.0]))
    assert symptom.shape == onset.shape == padding.shape == (2, 2)
    assert padding.tolist() == [[False, False], [True, True]]
    assert presentation.tolist() == [3.0, 1.0]
    empty = collate([np.zeros((0, 2))], np.array([1.0]))
    assert empty[0].shape == (1, 0)


def test_forward_shapes_including_all_empty_batch() -> None:
    m = model()
    syn, spe = m(*collate([np.array([[1, 0.5]]), np.zeros((0, 2))], np.array([2.0, 1.0])))
    assert syn.shape == (2, 4) and spe.shape == (2, 3)
    syn, _ = m(*collate([np.zeros((0, 2))], np.array([1.0])))
    assert torch.isfinite(syn).all()


def test_output_invariant_to_padding_and_event_order() -> None:
    m = model()
    seq = np.array([[1, 0.5], [2, 1.5], [4, 3.0]])
    with torch.no_grad():
        alone = m(*collate([seq], np.array([4.0])))[0]
        padded = m(*collate([seq, np.zeros((6, 2)) + [[0, 1.0]]], np.array([4.0, 5.0])))[0][:1]
        shuffled = m(*collate([seq[[2, 0, 1]]], np.array([4.0])))[0]
    torch.testing.assert_close(alone, padded, atol=1e-5, rtol=1e-5)
    torch.testing.assert_close(alone, shuffled, atol=1e-5, rtol=1e-5)


def toy_data(n: int = 400) -> tuple[list[np.ndarray], np.ndarray, np.ndarray, np.ndarray]:
    """Syndrome = whether symptom 1 is present; species follows the syndrome."""
    rng = np.random.default_rng(0)
    has = rng.random(n) < 0.5
    seqs = [np.array([[1, 0.5]]) if h else np.array([[2, 0.5]]) for h in has]
    return seqs, np.full(n, 2.0), has.astype(int), has.astype(int)


def test_fit_transformer_learns_toy_task_and_is_reproducible() -> None:
    seqs, pres, y_syn, y_sp = toy_data()
    idx = np.arange(len(seqs))
    params = {"d_model": 16, "n_heads": 2, "n_layers": 1, "max_epochs": 15, "patience": 5, "batch_size": 64, "lr": 3e-3}
    fit = fit_transformer(seqs, pres, y_syn, y_sp, idx[:300], idx[300:], 3, 4, 2, params, seed=1)
    p_syn, p_sp = predict_proba(fit.model, seqs, pres, idx[300:])
    assert p_syn.shape == (100, 4) and p_sp.shape == (100, 2)
    np.testing.assert_allclose(p_syn.sum(1), 1.0, atol=1e-5)
    assert (p_syn.argmax(1) == y_syn[300:]).mean() == 1.0
    again = fit_transformer(seqs, pres, y_syn, y_sp, idx[:300], idx[300:], 3, 4, 2, params, seed=1)
    np.testing.assert_allclose(predict_proba(again.model, seqs, pres, idx[300:])[0], p_syn, atol=1e-6)


def test_xgb_head_keeps_columns_for_classes_absent_in_training() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, 3))
    y = np.where(x[:, 0] > 0, 3, 1)  # classes 0 and 2 never occur
    head = XGBHead(4, {"n_estimators": 20, "early_stopping_rounds": 5}).fit(x[:150], y[:150], x[150:], y[150:])
    proba = head.predict_proba(x[150:])
    assert proba.shape == (50, 4)
    np.testing.assert_allclose(proba[:, [0, 2]], 0.0)
    assert (proba.argmax(1) == y[150:]).mean() > 0.9
