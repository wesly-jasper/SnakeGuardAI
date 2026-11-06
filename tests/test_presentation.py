"""Tests for src/data/presentation.py. Fixture bins are made up."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.generate import generate
from src.data.presentation import DELAY_COLUMNS, DelayDistribution, load_delay

BINS = [
    # profile, min, max, proportion, source_key, evidence, verified
    ("p", 0, 1, 0.3, "fake2026", "", False),
    ("p", 1, 6, 0.6, "fake2026", "", False),
    ("p", 24, None, 0.06, "fake2026", "", False),  # gap 6-24 allowed; sum 0.96
    ("q", 0, 2, 1.0, "fake2026", "", False),
]


def write_delay(directory: Path, rows: list[tuple]) -> Path:
    lines = [",".join(DELAY_COLUMNS)] + [",".join("" if v is None else str(v) for v in r) for r in rows]
    (directory / "presentation_delay.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return directory


def test_load_renormalises_and_closes_open_bin(knowledge_dir: Path) -> None:
    dist = load_delay(write_delay(knowledge_dir, BINS), "p", open_bin_max_hours=48)
    assert dist.lows == (0.0, 1.0, 24.0) and dist.highs == (1.0, 6.0, 48.0)
    assert sum(dist.probs) == pytest.approx(1.0)
    assert dist.probs[1] == pytest.approx(0.6 / 0.96)


def test_sample_matches_bin_proportions(knowledge_dir: Path) -> None:
    dist = load_delay(write_delay(knowledge_dir, BINS), "p", open_bin_max_hours=48)
    draws = np.array([dist.sample(np.random.default_rng([7, i])) for i in range(4000)])
    assert ((draws >= 0) & (draws <= 48)).all()
    assert not ((draws > 6) & (draws < 24)).any()
    assert np.mean(draws < 1) == pytest.approx(0.3 / 0.96, abs=0.03)
    assert np.mean(draws >= 24) == pytest.approx(0.06 / 0.96, abs=0.015)


def test_uniform_uses_one_draw() -> None:
    a, b = np.random.default_rng(3), np.random.default_rng(3)
    assert DelayDistribution.uniform(0.5, 24).sample(a) == b.uniform(0.5, 24)


@pytest.mark.parametrize(
    "rows, error",
    [
        ([("p", 0, 2, 0.5, "fake2026", "", False), ("p", 1, 3, 0.5, "fake2026", "", False)], "overlap"),
        ([("p", 2, 1, 1.0, "fake2026", "", False)], "min_hours < max_hours"),
        ([("p", 0, 1, 1.5, "fake2026", "", False)], "proportions"),
        ([("p", 0, 1, 1.0, "missing2020", "", False)], "citation"),
        ([("other", 0, 1, 1.0, "fake2026", "", False)], "no rows"),
    ],
)
def test_invalid_tables_raise(knowledge_dir: Path, rows: list[tuple], error: str) -> None:
    with pytest.raises(ValueError, match=error):
        load_delay(write_delay(knowledge_dir, rows), "p", open_bin_max_hours=48)


def test_generate_uses_profile(knowledge_dir: Path, tmp_path: Path) -> None:
    write_delay(knowledge_dir, BINS)
    out = generate({"name": "t", "seed": 1, "n_patients": 400, "knowledge_dir": str(knowledge_dir),
                    "output_dir": str(tmp_path / "ds"),
                    "presentation_delay": {"profile": "q", "open_bin_max_hours": 48}})
    hours = pd.read_csv(out / "patients.csv")["presentation_hours"]
    assert hours.between(0, 2).all()
    assert "cited profile `q`" in (out / "report.md").read_text(encoding="utf-8")


def test_repo_table_loads() -> None:
    root = Path(__file__).resolve().parents[1] / "knowledge"
    for profile in ["kerala_adult", "kerala_adult_cumulative", "srilanka_paediatric_hnpv"]:
        dist = load_delay(root, profile, open_bin_max_hours=48)
        assert sum(dist.probs) == pytest.approx(1.0)
