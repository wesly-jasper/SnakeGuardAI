"""Derive per-species context probabilities from the Wijayasekara et al. 2026 raw data.

Source: S1 Appendix (`Data.xlsx`, one row per bite, 4,708 bites, Anuradhapura, Sri Lanka)
of wijayasekara2026patterns (PLoS NTD 20(3):e0014092, CC BY 4.0). Download it into its own
folder under data/raw/ and pass the path:

    python -m src.data.wijayasekara data/raw/wijayasekara2026_s1/extracted/Data.xlsx

Definitions (match the simulator):
- night:  time of bite in [18:00, 06:00)
- indoor: bite place mentions house/home/inside/room and not garden/compound
- asleep: activity mentions "sleep"
Blank cells are excluded from each denominator. `joint_rows` also writes
knowledge/context_joint.csv: counts of every (night, indoor, asleep) combination over the
bites with all three recorded (complete cases), so the simulator can sample them jointly. On the krait and cobra rows these rules
reproduce the paper's Table 1 (krait indoor 61% vs 61.5%, asleep 62% vs 60.6%).
"""

from __future__ import annotations

import argparse
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
COLUMNS = ["Gender", "BitePlace", "Activity", "Time of Bite", "SiteOfBite", "Snake"]
SNAKE_CODES: dict[str, list[str]] = {
    "IK": ["Bungarus caeruleus"],
    "CBR": ["Naja naja"],
    "RV": ["Daboia russelii"],
    "Non-V": ["Ptyas mucosa", "Lycodon aulicus", "Fowlea piscator"],
}
SOURCE_KEY = "wijayasekara2026patterns"


def _column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref).group()
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch) - 64
    return index - 1


def read_first_sheet(path: str | Path) -> pd.DataFrame:
    """Read the first worksheet of an .xlsx file with the standard library only."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(SHEET_NS + "t")) for si in root.findall(SHEET_NS + "si")]
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.find(SHEET_NS + "sheetData").findall(SHEET_NS + "row"):
        cells: dict[int, str] = {}
        for cell in row.findall(SHEET_NS + "c"):
            value = cell.find(SHEET_NS + "v")
            if value is not None:
                cells[_column_index(cell.get("r"))] = shared[int(value.text)] if cell.get("t") == "s" else value.text
        rows.append(cells)
    width = max((max(r) + 1 for r in rows if r), default=0)
    table = [[r.get(i) for i in range(width)] for r in rows]
    return pd.DataFrame(table[1:], columns=table[0])


def context_flags(bites: pd.DataFrame) -> pd.DataFrame:
    """Add boolean night / indoor / asleep columns (NaN where the source cell is blank)."""
    missing = [c for c in COLUMNS if c not in bites.columns]
    if missing:
        raise ValueError(f"unexpected sheet layout, missing columns: {missing}")
    place = bites["BitePlace"].fillna("").str.lower().str.strip()
    activity = bites["Activity"].fillna("").str.lower().str.strip()
    hour = pd.to_numeric(bites["Time of Bite"], errors="coerce") * 24
    out = bites.copy()
    out["night"] = ((hour >= 18) | (hour < 6)).where(hour.notna())
    out["indoor"] = (place.str.contains("house|home|inside|room") & ~place.str.contains("garden|compound")).where(place != "")
    out["asleep"] = activity.str.contains("sleep").where(activity != "")
    return out


def context_rows(bites: pd.DataFrame) -> pd.DataFrame:
    """context_table.csv rows for the species covered by SNAKE_CODES."""
    flags = context_flags(bites)
    rows = []
    for code, species_list in SNAKE_CODES.items():
        group = flags[flags["Snake"] == code]
        for feature in ("night", "indoor", "asleep"):
            known = group[feature].dropna().astype(bool)
            if known.empty:
                continue
            k, n = int(known.sum()), len(known)
            pooled = " POOLED non-venomous, not species-specific;" if code == "Non-V" else ""
            evidence = (
                f"S1 Appendix Data.xlsx, Snake='{code}':{pooled} {k}/{n} "
                f"(derived by src/data/wijayasekara.py; {feature} definition in its docstring)"
            )
            for species in species_list:
                rows.append((species, feature, round(k / n, 3), SOURCE_KEY, evidence, False))
    return pd.DataFrame(rows, columns=["species", "feature", "probability", "source_key", "evidence", "verified"])


def joint_rows(bites: pd.DataFrame) -> pd.DataFrame:
    """context_joint.csv rows: complete-case counts of each (night, indoor, asleep) cell.

    All 8 cells are listed per snake code, including zero counts, so absent combinations
    are explicit. Pooled non-venomous counts are repeated for each non-venomous species.
    """
    flags = context_flags(bites)
    features = ["night", "indoor", "asleep"]
    rows = []
    for code, species_list in SNAKE_CODES.items():
        complete = flags.loc[flags["Snake"] == code, features].dropna().astype(bool)
        if complete.empty:
            continue
        counts = complete.value_counts()
        pooled = " POOLED non-venomous, not species-specific;" if code == "Non-V" else ""
        for night in (False, True):
            for indoor in (False, True):
                for asleep in (False, True):
                    k = int(counts.get((night, indoor, asleep), 0))
                    evidence = (
                        f"S1 Appendix Data.xlsx, Snake='{code}':{pooled} {k}/{len(complete)} complete cases "
                        "(derived by src/data/wijayasekara.py joint_rows)"
                    )
                    for species in species_list:
                        rows.append((species, night, indoor, asleep, k, SOURCE_KEY, evidence, False))
    return pd.DataFrame(
        rows, columns=["species", "night", "indoor", "asleep", "count", "source_key", "evidence", "verified"]
    )


def merge_into(context_table: pd.DataFrame, new_rows: pd.DataFrame) -> pd.DataFrame:
    """Replace (species, feature) rows in `context_table` with `new_rows`."""
    keys = set(zip(new_rows["species"], new_rows["feature"]))
    kept = context_table[[k not in keys for k in zip(context_table["species"], context_table["feature"])]]
    return pd.concat([kept, new_rows], ignore_index=True).sort_values(["species", "feature"]).reset_index(drop=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("xlsx", help="path to the S1 Appendix Data.xlsx")
    parser.add_argument("--context-table", default="knowledge/context_table.csv")
    parser.add_argument("--joint-table", default="knowledge/context_joint.csv")
    args = parser.parse_args(argv)
    bites = read_first_sheet(args.xlsx)
    new_rows = context_rows(bites)
    table = pd.read_csv(args.context_table, dtype={"source_key": str, "evidence": str})
    merge_into(table, new_rows).to_csv(args.context_table, index=False)
    print(new_rows.drop(columns="evidence").to_string(index=False))
    joint = joint_rows(bites)
    joint.to_csv(args.joint_table, index=False)
    print(f"wrote {len(joint)} joint context rows to {args.joint_table}")


if __name__ == "__main__":
    main()
