"""Bite-to-presentation delay distributions from knowledge/presentation_delay.csv.

Each profile is a set of cited, disjoint delay bins (min_hours, max_hours, proportion) from
one published series. Series rarely report 100% of patients: the unreported share
(1 - sum of proportions) is kept in `DelayDistribution.unreported` and written to each
dataset's meta.json, and the reported bins are renormalised (i.e. the unreported patients are
assumed to follow the reported distribution). A blank max_hours marks the open last bin
("> 24 h"); its upper bound is not reported, so the config supplies it
(`open_bin_max_hours`) as a documented assumption. The delay is sampled by picking a bin,
then uniformly within it (uniform-within-bin is also an assumption).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.knowledge import _check_verified, check_citations, read_bib_keys, read_table

DELAY_COLUMNS = ["profile", "min_hours", "max_hours", "proportion", "source_key", "evidence", "verified"]
SUM_TOLERANCE = 1e-6


@dataclass(frozen=True)
class DelayDistribution:
    """Piecewise-uniform delay in hours: bin i is [lows[i], highs[i]] with weight probs[i]."""

    lows: tuple[float, ...]
    highs: tuple[float, ...]
    probs: tuple[float, ...]
    unreported: float = 0.0  # share of the source series in no reported bin

    def __post_init__(self) -> None:
        if not (len(self.lows) == len(self.highs) == len(self.probs) >= 1):
            raise ValueError("delay bins need equal, non-zero numbers of lows, highs and probs")
        values = [*self.lows, *self.highs, *self.probs, self.unreported]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("delay bins must be finite")
        if any(lo < 0 or hi < lo for lo, hi in zip(self.lows, self.highs)):
            raise ValueError("delay bins need 0 <= low <= high")
        if any(p < 0 for p in self.probs) or not math.isclose(sum(self.probs), 1.0, abs_tol=SUM_TOLERANCE):
            raise ValueError("delay probabilities must be non-negative and sum to 1")
        if not 0 <= self.unreported < 1:
            raise ValueError("unreported share must be in [0, 1)")

    @classmethod
    def uniform(cls, lo: float, hi: float) -> "DelayDistribution":
        return cls((float(lo),), (float(hi),), (1.0,))

    def sample(self, rng: np.random.Generator) -> float:
        # A single bin uses one draw, so uniform ranges reproduce earlier datasets exactly.
        i = 0 if len(self.probs) == 1 else int(rng.choice(len(self.probs), p=self.probs))
        return float(rng.uniform(self.lows[i], self.highs[i]))

    def mean(self) -> float:
        return float(sum(p * (lo + hi) / 2 for lo, hi, p in zip(self.lows, self.highs, self.probs)))

    def summary(self) -> dict[str, object]:
        return {
            "bins": [[lo, hi, round(p, 4)] for lo, hi, p in zip(self.lows, self.highs, self.probs)],
            "unreported_share_of_source": round(self.unreported, 4),
            "mean_hours": round(self.mean(), 3),
        }


def validate_bins(bins: pd.DataFrame, profile: str, open_bin_max_hours: float) -> None:
    """Check one profile's raw bins before the open bin is closed.

    Proportions finite in [0, 1] with 0 < sum <= 1; bounds finite with 0 <= min < max; at most
    one open bin, which must be the last; no overlaps; open_bin_max_hours above the open bin.
    """
    if bins.empty:
        raise ValueError(f"presentation_delay.csv has no rows for profile {profile!r}")
    for col in ("min_hours", "max_hours", "proportion"):
        values = pd.to_numeric(bins[col], errors="raise").dropna().to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"profile {profile!r}: {col} must be finite")
    props = bins["proportion"]
    if props.isna().any() or not props.between(0, 1).all():
        raise ValueError(f"profile {profile!r}: proportions must be in [0, 1]")
    total = props.sum()
    if total <= 0 or total > 1 + SUM_TOLERANCE:
        raise ValueError(f"profile {profile!r}: proportions must have a sum in (0, 1], got {total:.4f}")
    if bins["min_hours"].isna().any():
        raise ValueError(f"profile {profile!r}: every bin needs min_hours")
    ordered = bins.sort_values("min_hours")
    open_bins = ordered["max_hours"].isna()
    if open_bins.sum() > 1 or (open_bins.any() and not open_bins.iloc[-1]):
        raise ValueError(f"profile {profile!r}: only the last bin may be open (blank max_hours)")
    if open_bins.any() and not (math.isfinite(open_bin_max_hours) and open_bin_max_hours > ordered["min_hours"].iloc[-1]):
        raise ValueError(f"profile {profile!r}: open_bin_max_hours must exceed the open bin's min_hours")
    closed = ordered[~open_bins]
    if (closed["min_hours"] < 0).any() or (closed["max_hours"] <= closed["min_hours"]).any():
        raise ValueError(f"profile {profile!r}: every bin needs 0 <= min_hours < max_hours")
    highs = ordered["max_hours"].fillna(open_bin_max_hours).to_numpy(dtype=float)
    if (ordered["min_hours"].to_numpy(dtype=float)[1:] < highs[:-1]).any():
        raise ValueError(f"profile {profile!r}: bins overlap")


def load_delay(
    knowledge_dir: str | Path,
    profile: str,
    open_bin_max_hours: float,
    require_verified: bool = False,
) -> DelayDistribution:
    """The cited delay distribution for `profile`; open bins end at `open_bin_max_hours`."""
    knowledge_dir = Path(knowledge_dir)
    table = read_table(knowledge_dir / "presentation_delay.csv", DELAY_COLUMNS)
    bins = table[table["profile"] == profile].copy()
    check_citations(bins, read_bib_keys(knowledge_dir / "sources.bib"), "presentation_delay.csv")
    if require_verified:
        _check_verified(bins, "presentation_delay.csv")
    open_bin_max_hours = float(open_bin_max_hours)
    validate_bins(bins, profile, open_bin_max_hours)
    bins["max_hours"] = bins["max_hours"].fillna(open_bin_max_hours)
    bins = bins.sort_values("min_hours")
    probs = bins["proportion"].to_numpy(dtype=float)
    return DelayDistribution(
        tuple(bins["min_hours"].astype(float)),
        tuple(bins["max_hours"].astype(float)),
        tuple(probs / probs.sum()),
        unreported=max(0.0, 1.0 - float(probs.sum())),
    )
