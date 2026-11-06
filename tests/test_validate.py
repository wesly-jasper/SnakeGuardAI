"""Tests for src/data/validate.py (the CI knowledge check). Fixture data is made up."""

from pathlib import Path

import pandas as pd

from src.data.knowledge import ORDER_COLUMNS
from src.data.validate import main
from tests.conftest import write_knowledge


def test_validate_passes_and_reports(knowledge_dir: Path, capsys) -> None:
    assert main(["--knowledge-dir", str(knowledge_dir)]) == 0
    assert "clinical_table.csv" in capsys.readouterr().out


def test_validate_fails_on_uncited_row(tmp_path: Path) -> None:
    clinical = [("Species a", "neuro", 0.0, 1.0, 1.0, "nosuchkey", "", True)]
    assert main(["--knowledge-dir", str(write_knowledge(tmp_path, clinical=clinical))]) == 1


def test_validate_fails_on_impossible_order(tmp_path: Path) -> None:
    clinical = [("Species a", "neuro", 6.0, 10.0, 1.0, "fake2026", "", True),
                ("Species a", "haemo", 0.0, 5.0, 1.0, "fake2026", "", True)]
    root = write_knowledge(tmp_path, clinical=clinical)
    pd.DataFrame([("*", "neuro", "haemo", "fake2026", "", True)], columns=ORDER_COLUMNS).to_csv(
        root / "onset_order.csv", index=False)
    assert main(["--knowledge-dir", str(root)]) == 1


def test_validate_require_verified(tmp_path: Path) -> None:
    clinical = [("Species a", "neuro", 0.0, 1.0, 1.0, "fake2026", "", False)]
    root = write_knowledge(tmp_path, clinical=clinical)
    assert main(["--knowledge-dir", str(root)]) == 0
    assert main(["--knowledge-dir", str(root), "--require-verified"]) == 1


def test_repo_knowledge_validates() -> None:
    assert main(["--knowledge-dir", str(Path(__file__).resolve().parents[1] / "knowledge")]) == 0
