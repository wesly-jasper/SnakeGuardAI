"""Regression tests for onset-order enforcement, cycle detection and copula/order diagnostics.

Fixture tables are made up; not clinical data. Statistical tests use fixed seeds.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.data.diagnostics import onset_diagnostics, summarise
from src.data.knowledge import ORDER_COLUMNS, find_cycle, load_knowledge
from src.data.simulator import (
    apply_order,
    build_specs,
    count_order_violations,
    draw_course,
    order_window_status,
    simulate_patients,
)
from tests.conftest import write_knowledge


def _kb(tmp_path: Path, windows: dict[str, tuple[float, float]], order: list[tuple[str, str]],
        freq: float = 1.0):
    clinical = [("Species a", s, lo, hi, freq, "fake2026", "", True) for s, (lo, hi) in windows.items()]
    root = write_knowledge(tmp_path, clinical=clinical)
    pd.DataFrame([("*", b, a, "fake2026", "", True) for b, a in order], columns=ORDER_COLUMNS).to_csv(
        root / "onset_order.csv", index=False)
    return load_knowledge(root, require_citations=True)


def _spec(tmp_path, windows, order, freq=1.0):
    with pytest.warns(UserWarning, match="Species b"):
        return build_specs(_kb(tmp_path, windows, order, freq))["Species a"]


def test_push_cannot_fix_partial_windows_and_is_reported() -> None:
    onsets = np.array([9.0, 1.0])  # before at 9 h, after window max 5 h
    present = np.array([True, True])
    pushed = apply_order(onsets, present, np.array([10.0, 5.0]), ((0, 1),))
    assert pushed[1] == 5.0
    assert count_order_violations(pushed, present, ((0, 1),)) == 1


def test_absent_sign_never_counts_as_violation() -> None:
    assert count_order_violations(np.array([9.0, 1.0]), np.array([True, False]), ((0, 1),)) == 0


def test_window_status(tmp_path: Path) -> None:
    spec = _spec(tmp_path, {"neuro": (0, 10), "haemo": (0, 5), "vomit": (0, 20)},
                 [("neuro", "haemo"), ("neuro", "vomit")])
    status = {(r["before"], r["after"]): r["status"] for r in order_window_status(spec)}
    assert status == {("neuro", "haemo"): "partial", ("neuro", "vomit"): "compatible"}


@pytest.mark.parametrize("windows, order", [
    ({"neuro": (6, 10), "haemo": (0, 5)}, [("neuro", "haemo")]),  # direct: before.min > after.max
    ({"neuro": (6, 10), "haemo": (0, 20), "vomit": (0, 5)}, [("neuro", "haemo"), ("haemo", "vomit")]),  # chain
])
def test_impossible_order_raises(tmp_path: Path, windows, order) -> None:
    kb = _kb(tmp_path, windows, order)
    with pytest.warns(UserWarning), pytest.raises(ValueError, match="onset order impossible"):
        build_specs(kb)


def test_partial_windows_satisfied_after_redraws(tmp_path: Path) -> None:
    kb = _kb(tmp_path, {"neuro": (0, 10), "haemo": (0, 5)}, [("neuro", "haemo")])
    with pytest.warns(UserWarning):
        patients = simulate_patients(kb, 1500, seed=0, species_weights={"Species a": 1.0})
    assert all(p.order_violations == 0 for p in patients)
    for p in patients:
        hours = {e.symptom: e.hours for e in p.course}
        assert hours["haemo"] >= hours["neuro"] - 1e-9


def test_unresolved_violations_are_flagged_not_hidden(tmp_path: Path) -> None:
    kb = _kb(tmp_path, {"neuro": (0, 10), "haemo": (0, 5)}, [("neuro", "haemo")])
    with pytest.warns(UserWarning):
        patients = simulate_patients(kb, 1500, seed=0, species_weights={"Species a": 1.0}, max_order_tries=1)
    flagged = [p for p in patients if p.order_violations]
    assert flagged  # P(neuro > 5) = 0.5, so the push alone fails often
    for p in patients:
        hours = {e.symptom: e.hours for e in p.course}
        violated = hours["haemo"] < hours["neuro"] - 1e-9
        assert violated == bool(p.order_violations)  # never claimed satisfied when violated


def test_max_order_tries_validated(tmp_path: Path) -> None:
    spec = _spec(tmp_path, {"neuro": (0, 10)}, [])
    with pytest.raises(ValueError, match="max_order_tries"):
        draw_course(spec, np.random.default_rng(0), max_order_tries=0)


@pytest.mark.parametrize("edges, expect_cycle", [
    ([("a", "b"), ("b", "c")], False),
    ([("a", "b"), ("b", "a")], True),
    ([("a", "b"), ("b", "c"), ("c", "a")], True),
    ([("a", "b"), ("a", "c"), ("c", "b")], False),
])
def test_find_cycle(edges, expect_cycle) -> None:
    cycle = find_cycle(edges)
    assert bool(cycle) == expect_cycle
    if cycle:
        assert cycle[0] == cycle[-1]


def test_cycle_in_onset_order_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cycle"):
        _kb(tmp_path, {"neuro": (0, 10), "haemo": (0, 10)}, [("neuro", "haemo"), ("haemo", "neuro")])


def test_cycle_across_species_and_star_rules_rejected(tmp_path: Path) -> None:
    clinical = [("Species a", s, 0, 10, 1.0, "fake2026", "", True) for s in ("neuro", "haemo")]
    root = write_knowledge(tmp_path, clinical=clinical)
    pd.DataFrame([("*", "neuro", "haemo", "fake2026", "", True),
                  ("Species a", "haemo", "neuro", "fake2026", "", True)], columns=ORDER_COLUMNS).to_csv(
        root / "onset_order.csv", index=False)
    with pytest.raises(ValueError, match="cycle for Species a"):
        load_knowledge(root)


# --- statistical regression tests (copula x order) ------------------------------------

def test_pre_order_onsets_are_uniform_in_window(tmp_path: Path) -> None:
    """Copula construction: over all draws, the pre-order onset is Uniform(window)."""
    spec = _spec(tmp_path, {"neuro": (2, 10), "haemo": (0, 5)}, [("neuro", "haemo")], freq=0.5)
    rng = np.random.default_rng(1)
    raw = np.array([draw_course(spec, rng, 0.8).raw_onsets for _ in range(4000)])
    assert stats.kstest(raw[:, 0], "uniform", args=(2, 8)).pvalue > 0.01
    assert stats.kstest(raw[:, 1], "uniform", args=(0, 5)).pvalue > 0.01


def test_presence_marginal_preserved_with_order(tmp_path: Path) -> None:
    spec = _spec(tmp_path, {"neuro": (0, 10), "haemo": (0, 5)}, [("neuro", "haemo")], freq=0.3)
    rng = np.random.default_rng(2)
    present = np.array([draw_course(spec, rng, 0.5).present for _ in range(5000)])
    for j in range(2):
        assert stats.binomtest(int(present[:, j].sum()), len(present), 0.3).pvalue > 0.01


def test_independent_unordered_onsets_uniform_among_present(tmp_path: Path) -> None:
    kb = _kb(tmp_path, {"neuro": (1, 9)}, [], freq=0.6)
    with pytest.warns(UserWarning):
        patients = simulate_patients(kb, 3000, seed=4, species_weights={"Species a": 1.0})
    hours = [e.hours for p in patients for e in p.course]
    assert stats.kstest(hours, "uniform", args=(1, 8)).pvalue > 0.01


def test_diagnostics_measure_order_shift(tmp_path: Path) -> None:
    compatible = _spec(tmp_path / "c", {"neuro": (0, 5), "haemo": (0, 10)}, [("neuro", "haemo")])
    marg, pairs = onset_diagnostics({"Species a": compatible}, 3000, 0, 0.0, 100)
    row = marg.set_index("symptom")
    assert row.loc["neuro", "share_changed"] == 0  # the earlier sign is never moved
    assert row.loc["haemo", "mean_after_order"] > row.loc["haemo", "mean_before_order"]
    assert pairs["violations_after_redraws"].sum() == 0
    assert row["raw_vs_uniform_p"].min() > 0.01

    partial = _spec(tmp_path / "p", {"neuro": (0, 10), "haemo": (0, 5)}, [("neuro", "haemo")])
    marg, pairs = onset_diagnostics({"Species a": partial}, 3000, 0, 0.0, 100)
    summary = summarise(marg, pairs)
    assert summary["order_rules_by_status"] == {"partial": 1}
    assert summary["order_violations_after_push_only"] > 0
    assert summary["order_violations_after_redraws"] == 0
    # Conditioning on the order pulls the earlier sign's onsets down: a measured shift.
    assert marg.set_index("symptom").loc["neuro", "mean_after_order"] < 5 - 0.5
