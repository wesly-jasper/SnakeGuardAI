"""Tests for src/data/wijayasekara.py. The fixture workbook is made up."""

import zipfile
from pathlib import Path

import pandas as pd
import pytest

from src.data.wijayasekara import context_flags, context_rows, merge_into, read_first_sheet

ROWS = [
    # BitePlace, Activity, Time of Bite (fraction of a day), Snake
    ("Inside the house", "Sleeping", 0.0833, "IK"),  # 02:00
    ("Home garden", "Walking", 0.5, "IK"),  # 12:00
    ("home", "sleeping on floor", 0.9, "IK"),  # 21:36
    ("Paddy field", None, 0.25, "RV"),  # 06:00, blank activity
    ("Road", "Walking", 0.8, "Non-V"),
]


def write_xlsx(path: Path, rows: list[tuple]) -> Path:
    """Minimal .xlsx with inline numbers and shared strings; row 4 skips the Activity cell."""
    header = ["Gender", "BitePlace", "Activity", "Time of Bite", "SiteOfBite", "Snake"]
    strings: list[str] = []

    def s(text: str) -> int:
        strings.append(text)
        return len(strings) - 1

    xml_rows = []
    for i, values in enumerate([header] + [("M", p, a, t, "toe", sn) for p, a, t, sn in rows], start=1):
        cells = []
        for j, v in enumerate(values):
            ref = f"{'ABCDEF'[j]}{i}"
            if v is None:
                continue
            if isinstance(v, float):
                cells.append(f'<c r="{ref}"><v>{v}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="s"><v>{s(str(v))}</v></c>')
        xml_rows.append(f'<row r="{i}">{"".join(cells)}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", f"<worksheet {ns}><sheetData>{''.join(xml_rows)}</sheetData></worksheet>")
        z.writestr("xl/sharedStrings.xml", f"<sst {ns}>" + "".join(f"<si><t>{t}</t></si>" for t in strings) + "</sst>")
    return path


@pytest.fixture
def bites(tmp_path: Path) -> pd.DataFrame:
    return read_first_sheet(write_xlsx(tmp_path / "Data.xlsx", ROWS))


def test_reader_keeps_columns_aligned_with_blank_cells(bites: pd.DataFrame) -> None:
    assert len(bites) == 5
    rv = bites[bites["Snake"] == "RV"].iloc[0]
    assert pd.isna(rv["Activity"]) and rv["BitePlace"] == "Paddy field"


def test_context_flags(bites: pd.DataFrame) -> None:
    flags = context_flags(bites)
    ik = flags[flags["Snake"] == "IK"]
    assert ik["night"].tolist() == [True, False, True]
    assert ik["indoor"].tolist() == [True, False, True]  # "Home garden" is outdoor
    assert ik["asleep"].tolist() == [True, False, True]
    assert pd.isna(flags[flags["Snake"] == "RV"]["asleep"].iloc[0])


def test_context_rows_and_merge(bites: pd.DataFrame) -> None:
    rows = context_rows(bites)
    krait = rows[(rows["species"] == "Bungarus caeruleus") & (rows["feature"] == "night")].iloc[0]
    assert krait["probability"] == pytest.approx(2 / 3, abs=1e-3)
    assert "2/3" in krait["evidence"]
    assert not rows["verified"].any()
    assert "asleep" not in set(rows[rows["species"] == "Daboia russelii"]["feature"])  # all blank
    assert set(rows[rows["feature"] == "night"]["species"]) >= {"Ptyas mucosa", "Lycodon aulicus", "Fowlea piscator"}

    old = pd.DataFrame(
        [("Bungarus caeruleus", "night", 0.1, "x", "", False), ("Hypnale hypnale", "night", 0.5, "y", "", False)],
        columns=rows.columns,
    )
    merged = merge_into(old, rows)
    assert merged.loc[(merged["species"] == "Bungarus caeruleus") & (merged["feature"] == "night"), "probability"].item() == pytest.approx(0.667)
    assert ((merged["species"] == "Hypnale hypnale") & (merged["probability"] == 0.5)).sum() == 1
