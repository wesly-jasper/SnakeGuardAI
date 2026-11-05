"""Sanity report for a simulated dataset. All numbers are SIMULATION results.

Contents:
- simulated symptom rates vs. knowledge-table frequencies (checks the simulator),
- syndrome mix per species,
- a rule-based syndromic baseline that applies the labelling rule to the events
  observed by presentation (the CLAUDE.md "rule-based syndromic table" baseline).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from src.data.knowledge import KnowledgeBase
from src.data.simulator import (
    DEFAULT_PRECEDENCE,
    DRY_LABEL,
    SYNDROMES,
    SyntheticPatient,
    derive_syndrome,
)

HEADER = "> **SIMULATION RESULTS** on synthetic patients from a literature-derived table. Not clinical evidence.\n"


def rule_predictions(
    patients: Sequence[SyntheticPatient],
    marker_of: dict[str, str],
    precedence: Sequence[str] = DEFAULT_PRECEDENCE,
) -> list[str]:
    """Syndrome from observed events only; the species is unknown, so any symptom counts."""
    return [
        derive_syndrome((e.symptom for e in p.observed_events), marker_of, True, precedence)
        for p in patients
    ]


def critical_error_rate(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    """Share of truly envenomed patients predicted as non-venomous/dry."""
    true = np.asarray(y_true)
    pred = np.asarray(y_pred)
    envenomed = true != DRY_LABEL
    return float((pred[envenomed] == DRY_LABEL).mean()) if envenomed.any() else float("nan")


def baseline_metrics(y_true: Sequence[str], y_pred: Sequence[str]) -> dict[str, float]:
    return {
        "n": len(y_true),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=list(SYNDROMES), average="macro", zero_division=0)),
        "critical_error_rate": critical_error_rate(y_true, y_pred),
    }


def frequency_check(patients: Sequence[SyntheticPatient], kb: KnowledgeBase) -> pd.DataFrame:
    """Per (species, symptom): table frequency vs. simulated rate among non-dry bites."""
    rows = []
    active = kb.clinical[kb.clinical["frequency"] > 0]
    for (species, symptom), group in active.groupby(["species", "symptom"]):
        bitten = [p for p in patients if p.species == species and not p.dry_bite]
        rate = np.mean([symptom in {e.symptom for e in p.course} for p in bitten]) if bitten else np.nan
        rows.append((species, symptom, float(group["frequency"].iloc[0]), float(rate), len(bitten)))
    return pd.DataFrame(rows, columns=["species", "symptom", "table_frequency", "simulated_rate", "n"])


def build_report(
    patients: Sequence[SyntheticPatient],
    splits: Sequence[str],
    kb: KnowledgeBase,
    precedence: Sequence[str] = DEFAULT_PRECEDENCE,
    notes: Sequence[str] = (),
) -> str:
    """Markdown sanity report for one simulated dataset."""
    labels = pd.DataFrame({"species": [p.species for p in patients], "syndrome": [p.venom_syndrome for p in patients]})
    test = [p for p, s in zip(patients, splits) if s == "test"]
    metrics = baseline_metrics([p.venom_syndrome for p in test], rule_predictions(test, kb.marker_of(), precedence))
    freq = frequency_check(patients, kb)
    parts = [
        "# Simulated dataset sanity report\n",
        HEADER,
        *(f"- {n}" for n in notes),
        "\n## Syndrome mix per species\n",
        pd.crosstab(labels["species"], labels["syndrome"]).to_markdown(),
        "\n## Simulated symptom rate vs. table frequency (non-dry bites)\n",
        freq.to_markdown(index=False, floatfmt=".3f"),
        "\n## Rule-based syndromic baseline (test split, observed events only)\n",
        pd.DataFrame([{**metrics, "n": str(metrics["n"])}]).to_markdown(index=False, floatfmt=".3f"),
        "\nThe critical error rate is the share of envenomed patients predicted as non-venomous/dry; "
        "here it comes from patients who present before any marker symptom appears.\n",
    ]
    return "\n".join(parts) + "\n"
