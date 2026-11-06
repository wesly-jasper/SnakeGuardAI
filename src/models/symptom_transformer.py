"""Symptom transformer (Phase 2): a transformer encoder over the observed symptom timeline.

Tokens:
- [CLS], whose output feeds the heads;
- a presentation token carrying the time from bite to presentation, so the model can
  read the absence of a symptom (no ptosis by 10 h means more than none by 1 h);
- one token per observed symptom: symptom embedding + encoding of its onset time and of
  the time elapsed between onset and presentation.

There is no positional encoding: order is carried by the onset times, and the output is
invariant to the order in which events are listed.

Heads: venom syndrome and species (top-k probabilities).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import torch
from torch import Tensor, nn


class TimeEncoding(nn.Module):
    """Sinusoidal encoding of log1p(hours) at geometric frequencies, projected to `d_model`."""

    def __init__(self, d_model: int, n_frequencies: int = 8, max_period: float = 16.0) -> None:
        super().__init__()
        freqs = 2 * math.pi / torch.logspace(-1, math.log10(max_period), n_frequencies)
        self.register_buffer("freqs", freqs)
        self.proj = nn.Linear(2 * n_frequencies + 1, d_model)

    def forward(self, hours: Tensor) -> Tensor:
        x = torch.log1p(hours.clamp(min=0.0)).unsqueeze(-1)
        angles = x * self.freqs
        return self.proj(torch.cat([torch.sin(angles), torch.cos(angles), x], dim=-1))


class SymptomTransformer(nn.Module):
    def __init__(
        self,
        n_symptoms: int,
        n_syndromes: int,
        n_species: int,
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.symptom_embedding = nn.Embedding(n_symptoms, d_model)
        self.onset_encoding = TimeEncoding(d_model)
        self.elapsed_encoding = TimeEncoding(d_model)
        self.presentation_encoding = TimeEncoding(d_model)
        self.cls = nn.Parameter(torch.zeros(1, 1, d_model))
        self.presentation = nn.Parameter(torch.zeros(1, 1, d_model))
        nn.init.normal_(self.cls, std=0.02)
        nn.init.normal_(self.presentation, std=0.02)
        layer = nn.TransformerEncoderLayer(
            d_model, n_heads, dim_feedforward=4 * d_model, dropout=dropout, batch_first=True, norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, n_layers, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(d_model)
        self.syndrome_head = nn.Linear(d_model, n_syndromes)
        self.species_head = nn.Linear(d_model, n_species)

    def forward(
        self, symptom: Tensor, onset: Tensor, padding: Tensor, presentation: Tensor,
    ) -> tuple[Tensor, Tensor]:
        """symptom (B, L) long, onset (B, L) hours, padding (B, L) True = pad,
        presentation (B,) hours. Returns (syndrome logits, species logits)."""
        batch = symptom.shape[0]
        elapsed = presentation.unsqueeze(1) - onset
        events = (
            self.symptom_embedding(symptom) + self.onset_encoding(onset) + self.elapsed_encoding(elapsed)
        )
        tokens = torch.cat([
            self.cls.expand(batch, -1, -1),
            self.presentation + self.presentation_encoding(presentation).unsqueeze(1),
            events,
        ], dim=1)
        mask = torch.cat([torch.zeros(batch, 2, dtype=torch.bool, device=padding.device), padding], dim=1)
        out = self.norm(self.encoder(tokens, src_key_padding_mask=mask)[:, 0])
        return self.syndrome_head(out), self.species_head(out)


def collate(
    sequences: Sequence[np.ndarray], presentation: np.ndarray
) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    """Pad (symptom index, onset hours) sequences to a batch; empty sequences are allowed."""
    length = max((len(s) for s in sequences), default=0)
    batch = len(sequences)
    symptom = torch.zeros(batch, length, dtype=torch.long)
    onset = torch.zeros(batch, length)
    padding = torch.ones(batch, length, dtype=torch.bool)
    for i, seq in enumerate(sequences):
        k = len(seq)
        if k:
            symptom[i, :k] = torch.as_tensor(seq[:, 0], dtype=torch.long)
            onset[i, :k] = torch.as_tensor(seq[:, 1], dtype=torch.float32)
            padding[i, :k] = False
    return symptom, onset, padding, torch.as_tensor(presentation, dtype=torch.float32)
