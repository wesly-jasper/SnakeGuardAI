"""Bite-to-presentation delay distributions from knowledge/presentation_delay.csv.

Each profile is a set of cited, disjoint delay bins (min_hours, max_hours, proportion) from
one published series. Proportions are renormalised over the reported bins (series rarely
sum to 100%). A blank max_hours marks the open last bin ("> 24 h"); its upper bound is not
reported, so the config supplies it (`open_bin_max_hours`) as a documented assumption.
The delay is sampled by picking a bin, then uniformly within it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.knowledge import check_citations, read_bib_keys, read_table

DELAY_COLUMNS = ["profile", "min_hours", "max_hours", "proportion", "source_key", "evidence", "verified"]


@dataclass(frozen=True)
class DelayDistribution:
    """Piecewise-uniform delay in hours: bin i is [lows[i], highs[i]] with weight probs[i]."""

    lows: tuple[float, ...]
    highs: tuple[float, ...]
    probs: tuple[float, ...]

    @classmethod
    def uniform(cls, lo: float, hi: float) -> "DelayDistribution":
        return cls((float(lo),), (float(hi),), (1.0,))

    def sample(self, rng: np.random.Generator) -> float:
        # A single bin uses one draw, so uniform ranges reproduce earlier datasets exactly.
        i = 0 if len(self.probs) == 1 else int(rng.choice(len(self.probs), p=self.probs))
        return float(rng.uniform(self.lows[i], self.highs[i]))

    def mean(self) -> float:
        return float(sum(p * (lo + hi) / 2 for lo, hi, p in zip(self.lows, self.highs, self.probs)))


def validate_bins(bins: pd.DataFrame, profile: str) -> None:
    """Bins must have probabilities in [0, 1], min < max, and must not overlap."""
    if bins.empty:
        raise ValueError(f"presentation_delay.csv has no rows for profile {profile!r}")
    if not bins["proportion"].between(0, 1).all() or bins["proportion"].sum() <= 0:
        raise ValueError(f"profile {profile!r}: proportions must be in [0, 1] with a positive sum")
    ordered = bins.sort_values("min_hours")
    if (ordered["min_hours"] < 0).any() or (ordered["max_hours"] <= ordered["min_hours"]).any():
        raise ValueError(f"profile {profile!r}: every bin needs 0 <= min_hours < max_hours")
    if (ordered["min_hours"].to_numpy()[1:] < ordered["max_hours"].to_numpy()[:-1]).any():
        raise ValueError(f"profile {profile!r}: bins overlap")


def load_delay(knowledge_dir: str | Path, profile: str, open_bin_max_hours: float) -> DelayDistribution:
    """The cited delay distribution for `profile`; open bins end at `open_bin_max_hours`."""
    knowledge_dir = Path(knowledge_dir)
    table = read_table(knowledge_dir / "presentation_delay.csv", DELAY_COLUMNS)
    bins = table[table["profile"] == profile].copy()
    check_citations(bins, read_bib_keys(knowledge_dir / "sources.bib"), "presentation_delay.csv")
    bins["max_hours"] = bins["max_hours"].fillna(float(open_bin_max_hours))
    validate_bins(bins, profile)
    bins = bins.sort_values("min_hours")
    probs = bins["proportion"].to_numpy(dtype=float)
    return DelayDistribution(
        tuple(bins["min_hours"].astype(float)),
        tuple(bins["max_hours"].astype(float)),
        tuple(probs / probs.sum()),
    )
