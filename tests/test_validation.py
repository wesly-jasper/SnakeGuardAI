"""Regression tests for probability/input validation, verification and joint context.

Fixture tables are made up; not clinical data.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.knowledge import JOINT_COLUMNS, load_knowledge, verification_summary
from src.data.presentation import DelayDistribution, load_delay
from src.data.simulator import assign_splits, sample_context, simulate_patients, species_probabilities
from tests.conftest import SPECIES, write_knowledge
from tests.test_presentation import BINS, write_delay


@pytest.fixture
def kb(knowledge_dir: Path):
    return load_knowledge(knowledge_dir, require_citations=True)


@pytest.mark.parametrize("weights", [
    {"Species a": -1.0, "Species b": 2.0},
    {"Species a": float("nan")},
    {"Species a": float("inf")},
    {"Species a": 0.0},
])
def test_bad_species_weights_rejected(weights) -> None:
    with pytest.raises(ValueError, match="species_weights"):
        species_probabilities(["Species a", "Species b"], weights)


def test_empty_species_list_rejected() -> None:
    with pytest.raises(ValueError, match="no species"):
        species_probabilities([], None)


@pytest.mark.parametrize("n", [-1, 2.0, True, None, "5"])
def test_bad_patient_counts_rejected(kb, n) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        simulate_patients(kb, n, seed=0)


def test_zero_patients_is_empty(kb) -> None:
    assert simulate_patients(kb, 0, seed=0) == []


def test_no_usable_species_raises(tmp_path: Path) -> None:
    species = [("Species a", "A", "venomous", 0.0, "fake2026", "", True)]
    kb = load_knowledge(write_knowledge(tmp_path, species=species, clinical=[], context=[]))
    with pytest.warns(UserWarning), pytest.raises(ValueError, match="no usable species"):
        simulate_patients(kb, 5, seed=0)


@pytest.mark.parametrize("rho", [float("nan"), -0.1, 1.1])
def test_bad_correlation_rejected(kb, rho) -> None:
    with pytest.raises(ValueError, match="severity_correlation"):
        simulate_patients(kb, 5, seed=0, severity_correlation=rho)


@pytest.mark.parametrize("hours", [(5.0, 1.0), (-1.0, 2.0), (0.0, float("inf"))])
def test_bad_presentation_range_rejected(kb, hours) -> None:
    with pytest.raises(ValueError):
        simulate_patients(kb, 5, seed=0, presentation_hours_range=hours)


@pytest.mark.parametrize("fractions", [{"a": float("nan"), "b": 1.0}, {}, {"a": -0.5, "b": 1.5}])
def test_bad_split_fractions_rejected(fractions) -> None:
    with pytest.raises(ValueError):
        assign_splits(10, fractions, seed=0)


def test_non_finite_onset_rejected(tmp_path: Path) -> None:
    clinical = [("Species a", "neuro", 0.0, float("inf"), 1.0, "fake2026", "", True)]
    with pytest.raises(ValueError, match="finite"):
        load_knowledge(write_knowledge(tmp_path, clinical=clinical))


def test_dry_bite_rate_out_of_range_rejected(tmp_path: Path) -> None:
    species = [("Species a", "A", "venomous", 1.5, "fake2026", "", True)] + SPECIES[1:]
    with pytest.raises(ValueError, match="dry_bite_rate"):
        load_knowledge(write_knowledge(tmp_path, species=species))


@pytest.mark.parametrize("kwargs", [
    {"lows": (0.0,), "highs": (1.0,), "probs": (0.5,)},  # does not sum to 1
    {"lows": (0.0, 1.0), "highs": (1.0, 2.0), "probs": (1.5, -0.5)},
    {"lows": (0.0,), "highs": (float("nan"),), "probs": (1.0,)},
    {"lows": (2.0,), "highs": (1.0,), "probs": (1.0,)},
    {"lows": (), "highs": (), "probs": ()},
    {"lows": (0.0,), "highs": (1.0,), "probs": (1.0,), "unreported": 1.0},
])
def test_delay_distribution_validated(kwargs) -> None:
    with pytest.raises(ValueError):
        DelayDistribution(**kwargs)


@pytest.mark.parametrize("rows, cap, error", [
    ([("p", 0, None, 0.5, "fake2026", "", False), ("p", 1, 2, 0.5, "fake2026", "", False)], 48, "only the last"),
    ([("p", 0, 1, 0.5, "fake2026", "", False), ("p", 24, None, 0.5, "fake2026", "", False)], 12, "open_bin_max_hours"),
    ([("p", 0, 1, 0.7, "fake2026", "", False), ("p", 1, 2, 0.7, "fake2026", "", False)], 48, "sum"),
    ([("p", None, 1, 1.0, "fake2026", "", False)], 48, "min_hours"),
])
def test_delay_bins_validated(knowledge_dir: Path, rows, cap, error) -> None:
    with pytest.raises(ValueError, match=error):
        load_delay(write_delay(knowledge_dir, rows), "p", open_bin_max_hours=cap)


def test_unreported_share_kept(knowledge_dir: Path) -> None:
    dist = load_delay(write_delay(knowledge_dir, BINS), "p", open_bin_max_hours=48)
    assert dist.unreported == pytest.approx(0.04)
    assert dist.summary()["unreported_share_of_source"] == pytest.approx(0.04)


def test_delay_require_verified(knowledge_dir: Path) -> None:
    with pytest.raises(ValueError, match="not human-verified"):
        load_delay(write_delay(knowledge_dir, BINS), "p", open_bin_max_hours=48, require_verified=True)


# --- verification across tables ------------------------------------------------------

def _joint(root: Path, rows: list[tuple]) -> Path:
    pd.DataFrame(rows, columns=JOINT_COLUMNS).to_csv(root / "context_joint.csv", index=False)
    return root


JOINT = [
    ("Species a", True, True, True, 3, "fake2026", "", False),
    ("Species a", True, False, False, 1, "fake2026", "", False),
    ("Species a", False, False, False, 0, "fake2026", "", False),
]


def test_verification_summary_covers_all_tables(knowledge_dir: Path) -> None:
    write_delay(knowledge_dir, BINS)
    _joint(knowledge_dir, JOINT)
    pd.DataFrame([("*", "neuro", "haemo", "fake2026", "", False)],
                 columns=["species", "before", "after", "source_key", "evidence", "verified"]).to_csv(
        knowledge_dir / "onset_order.csv", index=False)
    summary = verification_summary(knowledge_dir)
    assert set(summary) == {"species.csv", "clinical_table.csv", "context_table.csv", "context_joint.csv",
                            "onset_order.csv", "presentation_delay.csv"}
    assert summary["context_joint.csv"] == {"rows": 3, "unverified": 3}
    assert summary["presentation_delay.csv"]["unverified"] == len(BINS)
    assert summary["clinical_table.csv"]["unverified"] == 0


def test_require_verified_covers_joint_context(knowledge_dir: Path) -> None:
    _joint(knowledge_dir, JOINT)
    with pytest.raises(ValueError, match="context_joint.csv"):
        load_knowledge(knowledge_dir, require_verified=True)


@pytest.mark.parametrize("bad", [
    [("Species a", True, True, True, -1, "fake2026", "", True)],
    [("Species a", True, True, True, 1.5, "fake2026", "", True)],
    [("Species a", True, True, True, 1, "fake2026", "", True)] * 2,
    [("Species a", True, True, True, 0, "fake2026", "", True)],
    [("Species z", True, True, True, 1, "fake2026", "", True)],
])
def test_joint_context_validated(knowledge_dir: Path, bad) -> None:
    with pytest.raises(ValueError, match="context_joint"):
        load_knowledge(_joint(knowledge_dir, bad))


def test_joint_context_sampling(knowledge_dir: Path) -> None:
    kb = load_knowledge(_joint(knowledge_dir, JOINT))
    patients = [p for p in simulate_patients(kb, 3000, seed=0) if p.species == "Species a"]
    cells = pd.Series([(p.hour_of_day >= 18 or p.hour_of_day < 6, p.indoor, p.asleep) for p in patients])
    assert set(cells) <= {(True, True, True), (True, False, False)}  # zero-count cell never drawn
    assert (cells == (True, True, True)).mean() == pytest.approx(0.75, abs=0.03)
    # Joint sampling keeps the dependence the marginals lose: asleep implies indoor here.
    assert all(p.indoor for p in patients if p.asleep)


def test_marginal_context_path_unchanged() -> None:
    a, b = np.random.default_rng(5), np.random.default_rng(5)
    assert sample_context({"night": 0.5}, a) == sample_context({"night": 0.5}, b, None)


def test_checklist_covers_order_and_joint(knowledge_dir: Path) -> None:
    from src.data.checklist import unverified_rows

    _joint(knowledge_dir, JOINT)
    pd.DataFrame([("*", "neuro", "haemo", "fake2026", "", False)],
                 columns=["species", "before", "after", "source_key", "evidence", "verified"]).to_csv(
        knowledge_dir / "onset_order.csv", index=False)
    tables = set(unverified_rows(knowledge_dir)["table"])
    assert {"onset_order.csv", "context_joint.csv"} <= tables
