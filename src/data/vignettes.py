"""Blinded clinician review kit for simulated (and optionally real) patients.

    python -m src.data.vignettes --dataset data/processed/sim_v1 --n 40 --out data/processed/review_v1
    python -m src.data.vignettes ... --real data/raw/<real_cases_dir>   # mix in real cases

Writes to --out:
- vignettes.md   blinded case descriptions (no species, no label, no source)
- rating_form.csv one row per vignette for the rater: realism 1-5, syndrome guess, comments
- answer_key.csv  vignette -> source (simulated/real), patient_id, species, syndrome (keep
                 away from raters)

A dataset folder holds patients.csv and events.csv in the format written by
src/data/generate.py; real cases must use the same columns. Simulated cases are sampled
evenly across venom syndromes. See docs/clinician_review_protocol.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.knowledge import read_table, SYMPTOM_COLUMNS

REPO_ROOT = Path(__file__).resolve().parents[2]
RATING_COLUMNS = ["vignette", "realism_1_to_5", "syndrome_guess", "confidence_1_to_5", "comments"]


def load_dataset(folder: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    folder = Path(folder)
    return pd.read_csv(folder / "patients.csv"), pd.read_csv(folder / "events.csv")


def stratified_sample(patients: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """About n patients, spread evenly over venom syndromes."""
    groups = list(patients.groupby("venom_syndrome"))
    per_group = max(1, n // len(groups))
    picks = [g.sample(min(per_group, len(g)), random_state=seed) for _, g in groups]
    return pd.concat(picks)


def _flag(value: object, yes: str, no: str) -> str:
    if pd.isna(value):
        return "not recorded"
    return yes if str(value).lower() in {"true", "1"} else no


def describe(patient: pd.Series, events: pd.DataFrame, names: dict[str, str]) -> str:
    """Plain-text case: context, presentation time and the symptom timeline."""
    hour = patient["hour_of_day"]
    clock = "not recorded" if pd.isna(hour) else f"{int(hour):02d}:{int((hour % 1) * 60):02d}"
    lines = [
        f"- Time of bite: {clock}; location: {_flag(patient['indoor'], 'indoors', 'outdoors')}; "
        f"asleep when bitten: {_flag(patient['asleep'], 'yes', 'no')}",
        f"- Presented to hospital {patient['presentation_hours']:.1f} h after the bite",
        "- Symptom timeline (hours since bite):",
    ]
    timeline = events.sort_values("hours")
    marked = False
    for e in timeline.itertuples():
        if not marked and e.hours > patient["presentation_hours"]:
            lines.append("  - --- presentation ---")
            marked = True
        lines.append(f"  - {e.hours:.1f} h: {names.get(e.symptom, e.symptom)}")
    if not marked:
        lines.append("  - --- presentation ---")
    if timeline.empty:
        lines.append("  - no symptoms during follow-up")
    return "\n".join(lines)


def build_kit(
    cases: list[tuple[str, pd.DataFrame, pd.DataFrame]], names: dict[str, str], seed: int
) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    """cases: (source, patients, events). Returns (vignettes markdown, rating form, answer key)."""
    rows = []
    for source, patients, events in cases:
        for p in patients.itertuples(index=False):
            rows.append((source, p._asdict(), events[events["patient_id"] == p.patient_id]))
    order = np.random.default_rng(seed).permutation(len(rows))
    parts = [
        "# Snakebite case review (blinded)",
        "",
        "Rate each case for realism (1 = implausible, 5 = indistinguishable from a real patient) and",
        "give your syndrome guess from the information up to the presentation line only:",
        "neurotoxic / haemotoxic / local-only / non-venomous-dry. Do not look anything up.",
        "",
    ]
    key = []
    for number, i in enumerate(order, start=1):
        source, patient, events = rows[i]
        vid = f"V{number:03d}"
        parts += [f"## {vid}", "", describe(pd.Series(patient), events, names), ""]
        key.append((vid, source, patient["patient_id"], patient.get("species"), patient.get("venom_syndrome")))
    form = pd.DataFrame([(k[0], "", "", "", "") for k in key], columns=RATING_COLUMNS)
    answer = pd.DataFrame(key, columns=["vignette", "source", "patient_id", "species", "venom_syndrome"])
    return "\n".join(parts), form, answer


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", required=True, help="simulated dataset folder")
    parser.add_argument("--real", help="optional folder of real cases in the same format")
    parser.add_argument("--n", type=int, default=40, help="number of simulated cases")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    names = dict(read_table(REPO_ROOT / "knowledge" / "symptoms.csv", SYMPTOM_COLUMNS)[["symptom", "definition"]].values)
    patients, events = load_dataset(args.dataset)
    cases = [("simulated", stratified_sample(patients, args.n, args.seed), events)]
    if args.real:
        cases.append(("real", *load_dataset(args.real)))
    text, form, answer = build_kit(cases, names, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "vignettes.md").write_text(text, encoding="utf-8")
    form.to_csv(out / "rating_form.csv", index=False)
    answer.to_csv(out / "answer_key.csv", index=False)
    print(f"wrote {len(form)} vignettes to {out}")


if __name__ == "__main__":
    main()
