"""Training loop for the symptom transformer: multi-task cross-entropy, AdamW,
early stopping on a validation subset of the training split."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import torch
from torch import nn

from src.models.symptom_transformer import SymptomTransformer, collate

DEFAULT_TRAINING: dict[str, Any] = {
    "d_model": 64,
    "n_heads": 4,
    "n_layers": 2,
    "dropout": 0.1,
    "lr": 1e-3,
    "weight_decay": 1e-2,
    "batch_size": 256,
    "max_epochs": 60,
    "patience": 8,
    "species_loss_weight": 1.0,
}
MODEL_KEYS = ("d_model", "n_heads", "n_layers", "dropout")


@dataclass
class FitResult:
    model: SymptomTransformer
    history: list[dict[str, float]] = field(default_factory=list)
    best_epoch: int = 0


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def _batches(index: np.ndarray, batch_size: int, rng: np.random.Generator | None) -> list[np.ndarray]:
    order = rng.permutation(index) if rng is not None else index
    return [order[i:i + batch_size] for i in range(0, len(order), batch_size)]


def _forward(model: SymptomTransformer, sequences: list[np.ndarray], presentation: np.ndarray, idx: np.ndarray):
    return model(*collate([sequences[i] for i in idx], presentation[idx]))


def evaluate_loss(
    model: SymptomTransformer, sequences: list[np.ndarray], presentation: np.ndarray,
    y_syndrome: np.ndarray, y_species: np.ndarray, index: np.ndarray, batch_size: int, species_weight: float,
) -> float:
    loss_fn = nn.CrossEntropyLoss(reduction="sum")
    model.eval()
    total = 0.0
    with torch.no_grad():
        for idx in _batches(index, batch_size, None):
            syn, spe = _forward(model, sequences, presentation, idx)
            total += loss_fn(syn, torch.as_tensor(y_syndrome[idx])).item()
            total += species_weight * loss_fn(spe, torch.as_tensor(y_species[idx])).item()
    return total / max(1, len(index))


def fit_transformer(
    sequences: list[np.ndarray],
    presentation: np.ndarray,
    y_syndrome: np.ndarray,
    y_species: np.ndarray,
    train_index: np.ndarray,
    val_index: np.ndarray,
    n_symptoms: int,
    n_syndromes: int,
    n_species: int,
    params: dict[str, Any] | None = None,
    seed: int = 0,
) -> FitResult:
    """Train on `train_index`, keep the weights with the lowest validation loss."""
    cfg = {**DEFAULT_TRAINING, **(params or {})}
    set_seed(seed)
    rng = np.random.default_rng(seed)
    model = SymptomTransformer(n_symptoms, n_syndromes, n_species, **{k: cfg[k] for k in MODEL_KEYS})
    optimiser = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    loss_fn = nn.CrossEntropyLoss()
    w = float(cfg["species_loss_weight"])
    best = (float("inf"), 0, copy.deepcopy(model.state_dict()))
    history: list[dict[str, float]] = []
    for epoch in range(1, int(cfg["max_epochs"]) + 1):
        model.train()
        running = 0.0
        for idx in _batches(train_index, int(cfg["batch_size"]), rng):
            syn, spe = _forward(model, sequences, presentation, idx)
            loss = loss_fn(syn, torch.as_tensor(y_syndrome[idx])) + w * loss_fn(spe, torch.as_tensor(y_species[idx]))
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
            running += loss.item() * len(idx)
        val = evaluate_loss(model, sequences, presentation, y_syndrome, y_species, val_index, int(cfg["batch_size"]), w)
        history.append({"epoch": epoch, "train_loss": running / len(train_index), "val_loss": val})
        if val < best[0]:
            best = (val, epoch, copy.deepcopy(model.state_dict()))
        elif epoch - best[1] >= int(cfg["patience"]):
            break
    model.load_state_dict(best[2])
    model.eval()
    return FitResult(model, history, best[1])


def predict_proba(
    model: SymptomTransformer, sequences: list[np.ndarray], presentation: np.ndarray,
    index: np.ndarray, batch_size: int = 1024,
) -> tuple[np.ndarray, np.ndarray]:
    """Softmax probabilities (syndrome, species) for the patients in `index`."""
    model.eval()
    syndrome, species = [], []
    with torch.no_grad():
        for idx in _batches(index, batch_size, None):
            syn, spe = _forward(model, sequences, presentation, idx)
            syndrome.append(torch.softmax(syn, -1).numpy())
            species.append(torch.softmax(spe, -1).numpy())
    return np.concatenate(syndrome), np.concatenate(species)
