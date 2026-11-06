"""Validate the knowledge base schema and citations (used by CI).

    python -m src.data.validate [--knowledge-dir knowledge] [--require-verified]

Checks, failing with exit code 1 on the first error:
- every table loads and passes its schema checks (src/data/knowledge.py), including
  onset-order cycles and the joint context counts;
- every row that the simulator can use cites keys present in sources.bib;
- no onset order is impossible given the onset windows, both with cited windows only and
  with the 0-24 h fallback used by the labelled sensitivity runs;
- every presentation-delay profile loads with valid bins.
Prints rows / unverified rows per evidence table. `--require-verified` also fails when any
row is unverified (for use once human verification is complete).
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

from src.data.knowledge import check_citations, load_knowledge, read_bib_keys, read_table, verification_summary
from src.data.presentation import DELAY_COLUMNS, load_delay
from src.data.simulator import build_specs

FALLBACK_CHECK = (0.0, 24.0)
OPEN_BIN_CHECK = 48.0


def validate(knowledge_dir: Path, require_verified: bool = False) -> dict[str, dict[str, int]]:
    """Run every check; raises ValueError on the first failure. Returns the verification summary."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # placeholders are reported by the loader elsewhere
        kb = load_knowledge(knowledge_dir, require_verified=require_verified, allow_missing_onset=True)
        bib = read_bib_keys(knowledge_dir / "sources.bib")
        venomous = kb.species[kb.species["group"] == "venomous"]
        check_citations(venomous[venomous["dry_bite_rate"].notna()], bib, "species.csv")
        check_citations(kb.clinical, bib, "clinical_table.csv")
        check_citations(kb.context, bib, "context_table.csv")
        check_citations(kb.onset_order, bib, "onset_order.csv")
        check_citations(kb.context_joint, bib, "context_joint.csv")
        build_specs(kb, None)
        build_specs(kb, FALLBACK_CHECK)
    delay_path = knowledge_dir / "presentation_delay.csv"
    if delay_path.exists():
        for profile in read_table(delay_path, DELAY_COLUMNS)["profile"].unique():
            load_delay(knowledge_dir, profile, OPEN_BIN_CHECK, require_verified=require_verified)
    return verification_summary(knowledge_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--knowledge-dir", default="knowledge")
    parser.add_argument("--require-verified", action="store_true")
    args = parser.parse_args(argv)
    try:
        summary = validate(Path(args.knowledge_dir), args.require_verified)
    except ValueError as err:
        print(f"knowledge validation FAILED: {err}", file=sys.stderr)
        return 1
    print("knowledge validation passed")
    for table, counts in summary.items():
        print(f"  {table}: {counts['rows']} rows, {counts['unverified']} unverified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
