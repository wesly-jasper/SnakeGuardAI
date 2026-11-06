"""Load and validate the literature-derived clinical knowledge base in knowledge/.

Files (see docs/phase1_plan.md):
- symptoms.csv        controlled symptom vocabulary with its syndrome marker
- species.csv         one row per species: group and dry-bite rate
- clinical_table.csv  one row per (species, symptom): onset window and frequency
- context_table.csv   one row per (species, feature): probability the feature is true
- onset_order.csv     optional; (species or *, before, after): cited order of onset
- context_joint.csv   optional; (species, night, indoor, asleep): cited joint counts
- presentation_delay.csv  bite-to-presentation delay bins (loaded by src/data/presentation.py)

Every number must be cited. Rows with blank numbers (placeholders) are skipped with a
warning unless `require_citations=True`, which refuses blank or uncited rows.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

MARKERS: frozenset[str] = frozenset({"neurotoxic", "haemotoxic", "local", "none"})
GROUPS: frozenset[str] = frozenset({"venomous", "non-venomous"})
CONTEXT_FEATURES: frozenset[str] = frozenset({"night", "indoor", "asleep"})
KEY_SEPARATOR = ";"

SYMPTOM_COLUMNS: list[str] = ["symptom", "marker", "definition"]
SPECIES_COLUMNS: list[str] = [
    "species", "common_name", "group", "dry_bite_rate", "source_key", "evidence", "verified",
]
CLINICAL_COLUMNS: list[str] = [
    "species", "symptom", "onset_min_hours", "onset_max_hours", "frequency",
    "source_key", "evidence", "verified",
]
CONTEXT_COLUMNS: list[str] = [
    "species", "feature", "probability", "source_key", "evidence", "verified",
]
ORDER_COLUMNS: list[str] = ["species", "before", "after", "source_key", "evidence", "verified"]
JOINT_COLUMNS: list[str] = [
    "species", "night", "indoor", "asleep", "count", "source_key", "evidence", "verified",
]
JOINT_FEATURES: tuple[str, ...] = ("night", "indoor", "asleep")
# Every table with numbers and a `verified` column; used by verification_summary().
EVIDENCE_TABLES: tuple[str, ...] = (
    "species.csv", "clinical_table.csv", "context_table.csv", "context_joint.csv",
    "onset_order.csv", "presentation_delay.csv",
)
ALL_SPECIES = "*"


@dataclass(frozen=True)
class KnowledgeBase:
    symptoms: pd.DataFrame
    species: pd.DataFrame
    clinical: pd.DataFrame
    context: pd.DataFrame
    onset_order: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=ORDER_COLUMNS))
    context_joint: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=JOINT_COLUMNS))

    def marker_of(self) -> dict[str, str]:
        return dict(zip(self.symptoms["symptom"], self.symptoms["marker"]))


def read_bib_keys(bib_path: str | Path) -> set[str]:
    """Return the citation keys defined in a BibTeX file."""
    text = Path(bib_path).read_text(encoding="utf-8")
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))


def split_keys(source_key: str) -> list[str]:
    """Split a `;`-separated source_key cell into individual citation keys."""
    return [k.strip() for k in str(source_key).split(KEY_SEPARATOR) if k.strip()]


def read_table(path: str | Path, columns: list[str]) -> pd.DataFrame:
    """Read a knowledge CSV, check its columns and normalise text/verified cells."""
    path = Path(path)
    table = pd.read_csv(path, dtype={"source_key": "string", "evidence": "string"})
    missing = [c for c in columns if c not in table.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")
    table = table[columns].copy()
    for col in ("source_key", "evidence"):
        if col in table:
            table[col] = table[col].fillna("").astype(str).str.strip()
    if "verified" in table:
        table["verified"] = table["verified"].map(_parse_bool).astype(bool)
    return table


def _parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def check_citations(table: pd.DataFrame, bib_keys: set[str], name: str) -> None:
    """Raise if any row has no source_key or cites a key missing from sources.bib."""
    bad = [
        i for i, cell in table["source_key"].items()
        if not split_keys(cell) or any(k not in bib_keys for k in split_keys(cell))
    ]
    if bad:
        raise ValueError(
            f"{name}: {len(bad)} row(s) lack a citation in sources.bib: "
            f"{table.loc[bad, 'source_key'].tolist()}"
        )


def drop_incomplete(
    table: pd.DataFrame, numeric: list[str], name: str, strict: bool
) -> pd.DataFrame:
    """Drop rows with blank numeric cells (warn), or raise when `strict`.

    A clinical row with frequency 0 (a documented absence) needs no onset window.
    """
    incomplete = table[numeric].isna().any(axis=1)
    if "frequency" in numeric:
        incomplete &= ~(table["frequency"] == 0)
    if not incomplete.any():
        return table
    if strict:
        raise ValueError(f"{name}: {int(incomplete.sum())} row(s) have blank numeric cells")
    warnings.warn(f"skipping {int(incomplete.sum())} incomplete row(s) in {name}", stacklevel=3)
    return table[~incomplete].reset_index(drop=True)


def _check_probability(table: pd.DataFrame, col: str, name: str) -> None:
    values = pd.to_numeric(table[col], errors="raise").dropna()
    if not values.between(0, 1).all():
        raise ValueError(f"{name}: {col} must be a finite number within [0, 1]")


def _check_finite(table: pd.DataFrame, cols: list[str], name: str) -> None:
    for col in cols:
        values = pd.to_numeric(table[col], errors="raise").dropna()
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{name}: {col} must be finite")


def _check_members(values: pd.Series, allowed: set[str] | frozenset[str], what: str) -> None:
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"unknown {what}: {unknown}")


def validate_symptoms(symptoms: pd.DataFrame) -> None:
    _check_members(symptoms["marker"], MARKERS, "marker")
    if symptoms["symptom"].duplicated().any():
        raise ValueError("symptoms.csv has duplicate symptoms")


def validate_species(species: pd.DataFrame) -> None:
    _check_members(species["group"], GROUPS, "group")
    if species["species"].duplicated().any():
        raise ValueError("species.csv has duplicate species")
    _check_probability(species, "dry_bite_rate", "species.csv")


def validate_clinical(clinical: pd.DataFrame, kb_species: set[str], vocab: set[str]) -> None:
    _check_members(clinical["species"], kb_species, "species in clinical_table.csv")
    _check_members(clinical["symptom"], vocab, "symptom in clinical_table.csv")
    _check_probability(clinical, "frequency", "clinical_table.csv")
    _check_finite(clinical, ["onset_min_hours", "onset_max_hours"], "clinical_table.csv")
    if (clinical["onset_min_hours"] < 0).any():
        raise ValueError("onset_min_hours must be >= 0")
    if (clinical["onset_min_hours"] > clinical["onset_max_hours"]).any():
        raise ValueError("onset_min_hours must be <= onset_max_hours")
    if clinical.duplicated(["species", "symptom"]).any():
        raise ValueError("clinical_table.csv has duplicate (species, symptom) rows")


def validate_context(context: pd.DataFrame, kb_species: set[str]) -> None:
    _check_members(context["species"], kb_species, "species in context_table.csv")
    _check_members(context["feature"], CONTEXT_FEATURES, "context feature")
    _check_probability(context, "probability", "context_table.csv")
    if context.duplicated(["species", "feature"]).any():
        raise ValueError("context_table.csv has duplicate (species, feature) rows")


def validate_order(order: pd.DataFrame, kb_species: set[str], vocab: set[str]) -> None:
    _check_members(order["species"], kb_species | {ALL_SPECIES}, "species in onset_order.csv")
    _check_members(pd.concat([order["before"], order["after"]]), vocab, "symptom in onset_order.csv")
    if (order["before"] == order["after"]).any():
        raise ValueError("onset_order.csv: a symptom cannot precede itself")
    for species in sorted(kb_species | {ALL_SPECIES}):
        cycle = find_cycle(order_edges(order, species))
        if cycle:
            raise ValueError(f"onset_order.csv: cycle for {species}: {' -> '.join(cycle)}")


def order_edges(order: pd.DataFrame, species: str) -> list[tuple[str, str]]:
    """(before, after) rules that apply to `species` (its own plus the `*` rules)."""
    rules = order[order["species"].isin([species, ALL_SPECIES])]
    return list(dict.fromkeys(zip(rules["before"], rules["after"])))


def find_cycle(edges: list[tuple[str, str]]) -> list[str]:
    """A cycle in the directed graph `edges` as [a, b, ..., a], or [] if it is acyclic."""
    graph: dict[str, list[str]] = {}
    for before, after in edges:
        graph.setdefault(before, []).append(after)
    state: dict[str, int] = {}  # 1 = on the current path, 2 = finished
    path: list[str] = []

    def visit(node: str) -> list[str]:
        state[node] = 1
        path.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt]
            if nxt not in state:
                found = visit(nxt)
                if found:
                    return found
        state[node] = 2
        path.pop()
        return []

    for node in list(graph):
        if node not in state:
            found = visit(node)
            if found:
                return found
    return []


def validate_joint(joint: pd.DataFrame, kb_species: set[str]) -> None:
    _check_members(joint["species"], kb_species, "species in context_joint.csv")
    counts = pd.to_numeric(joint["count"], errors="raise")
    if counts.isna().any() or (counts < 0).any() or (counts % 1 != 0).any():
        raise ValueError("context_joint.csv: count must be a non-negative integer")
    if joint.duplicated(["species", *JOINT_FEATURES]).any():
        raise ValueError("context_joint.csv has duplicate (species, night, indoor, asleep) cells")
    for species, group in joint.groupby("species"):
        if group["count"].sum() <= 0:
            raise ValueError(f"context_joint.csv: {species} has no observations")


def read_joint(root: Path) -> pd.DataFrame:
    path = root / "context_joint.csv"
    if not path.exists():
        return pd.DataFrame(columns=JOINT_COLUMNS)
    joint = read_table(path, JOINT_COLUMNS)
    for col in JOINT_FEATURES:
        if not joint[col].astype(str).str.lower().isin({"true", "false"}).all():
            raise ValueError(f"context_joint.csv: {col} must be true/false")
        joint[col] = joint[col].astype(str).str.lower() == "true"
    return joint


def verification_summary(knowledge_dir: str | Path) -> dict[str, dict[str, int]]:
    """Rows and unverified rows per evidence table (all rows in the file, used or not)."""
    root = Path(knowledge_dir)
    summary = {}
    for name in EVIDENCE_TABLES:
        path = root / name
        if not path.exists():
            continue
        verified = pd.read_csv(path, usecols=["verified"])["verified"].map(_parse_bool)
        summary[name] = {"rows": int(len(verified)), "unverified": int((~verified).sum())}
    return summary


def read_order(root: Path) -> pd.DataFrame:
    path = root / "onset_order.csv"
    return read_table(path, ORDER_COLUMNS) if path.exists() else pd.DataFrame(columns=ORDER_COLUMNS)


def load_knowledge(
    knowledge_dir: str | Path,
    require_citations: bool = False,
    require_verified: bool = False,
    allow_missing_onset: bool = False,
) -> KnowledgeBase:
    """Load all knowledge tables from `knowledge_dir` and cross-validate them.

    With `allow_missing_onset=True`, clinical rows with a frequency but a blank onset
    bound are kept; the simulator then fills the bound from its cited fallback window.
    """
    root = Path(knowledge_dir)
    symptoms = read_table(root / "symptoms.csv", SYMPTOM_COLUMNS)
    species = read_table(root / "species.csv", SPECIES_COLUMNS)
    clinical = read_table(root / "clinical_table.csv", CLINICAL_COLUMNS)
    context = read_table(root / "context_table.csv", CONTEXT_COLUMNS)
    order = read_order(root)
    joint = read_joint(root)

    venomous = species["group"] == "venomous"
    dry_needed = species[venomous]
    required = ["frequency"] if allow_missing_onset else ["onset_min_hours", "onset_max_hours", "frequency"]
    clinical = drop_incomplete(clinical, required, "clinical_table.csv", require_citations)
    context = drop_incomplete(context, ["probability"], "context_table.csv", require_citations)
    if require_citations:
        bib_keys = read_bib_keys(root / "sources.bib")
        drop_incomplete(dry_needed, ["dry_bite_rate"], "species.csv", strict=True)
        check_citations(dry_needed, bib_keys, "species.csv")
        check_citations(clinical, bib_keys, "clinical_table.csv")
        check_citations(context, bib_keys, "context_table.csv")
        check_citations(order, bib_keys, "onset_order.csv")
        check_citations(joint, bib_keys, "context_joint.csv")
    elif dry_needed["dry_bite_rate"].isna().any():
        warnings.warn(
            "dry_bite_rate blank for "
            f"{dry_needed.loc[dry_needed['dry_bite_rate'].isna(), 'species'].tolist()}; "
            "the simulator treats it as 0",
            stacklevel=2,
        )
    if require_verified:
        _check_verified(clinical, "clinical_table.csv")
        _check_verified(context, "context_table.csv")
        _check_verified(dry_needed, "species.csv")
        _check_verified(order, "onset_order.csv")
        _check_verified(joint, "context_joint.csv")

    validate_symptoms(symptoms)
    validate_species(species)
    validate_clinical(clinical, set(species["species"]), set(symptoms["symptom"]))
    validate_context(context, set(species["species"]))
    validate_order(order, set(species["species"]), set(symptoms["symptom"]))
    validate_joint(joint, set(species["species"]))
    return KnowledgeBase(symptoms, species, clinical, context, order, joint)


def _check_verified(table: pd.DataFrame, name: str) -> None:
    if not table["verified"].all():
        raise ValueError(f"{name}: {int((~table['verified']).sum())} row(s) not human-verified")


OVERRIDE_TABLES: dict[str, list[str]] = {
    "species": ["species"],
    "clinical": ["species", "symptom"],
    "context": ["species", "feature"],
}


def apply_overrides(kb: KnowledgeBase, overrides: list[dict] | None) -> KnowledgeBase:
    """Return a copy of `kb` with single values replaced, for sensitivity analyses.

    Each override is {"table": species|clinical|context, "match": {key columns},
    "set": {column: value}} and must match exactly one row. The CSVs are not touched.
    """
    if not overrides:
        return kb
    tables = {name: getattr(kb, name).copy() for name in OVERRIDE_TABLES}
    for spec in overrides:
        name = spec["table"]
        if name not in OVERRIDE_TABLES:
            raise ValueError(f"override table must be one of {sorted(OVERRIDE_TABLES)}")
        table = tables[name]
        if set(spec["match"]) != set(OVERRIDE_TABLES[name]):
            raise ValueError(f"override on {name} must match on {OVERRIDE_TABLES[name]}")
        mask = pd.Series(True, index=table.index)
        for col, value in spec["match"].items():
            mask &= table[col] == value
        if mask.sum() != 1:
            raise ValueError(f"override {spec['match']} matched {int(mask.sum())} rows in {name}")
        for col, value in spec["set"].items():
            if col not in table.columns:
                raise ValueError(f"unknown column {col} in {name}")
            table.loc[mask, col] = value
    return KnowledgeBase(
        kb.symptoms, tables["species"], tables["clinical"], tables["context"], kb.onset_order,
        kb.context_joint,
    )
