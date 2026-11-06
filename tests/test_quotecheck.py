"""Tests for src/data/quotecheck.py. No network: fetches are faked. Texts are made up."""

import json
from pathlib import Path

import pytest

from src.data.quotecheck import (
    EUROPEPMC,
    SourceStore,
    check_knowledge,
    check_row,
    compact,
    extract_fragments,
    fetch_source_text,
    fragment_in,
    fragment_parts,
    main,
    mentioned_keys,
    normalise,
    parse_bib,
    render,
    row_status,
    xml_to_text,
)
from tests.conftest import write_knowledge

BIB = """@article{alpha2020,
  title = {A {nested} title},
  doi   = {10.1/alpha},
  url   = {https://pmc.ncbi.nlm.nih.gov/articles/PMC123/}
}
@misc{beta2021,
  url = {https://example.org/beta}
}
"""
ALPHA_XML = (b"<?xml version='1.0'?><article><body><p>Ptosis was first detected 30&#x2009;minutes "
             b"to 4\xe2\x80\x93hours after the bite.</p><table><tr><td>Pain</td><td>53 (96)</td></tr>"
             b"</table><p>Only six bites occurred within the patient\xe2\x80\x99s house.</p></body></article>")


def fake_fetch(pages: dict[str, bytes]):
    calls: list[str] = []

    def fetch(url: str) -> bytes | None:
        calls.append(url)
        return pages.get(url)

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


# --- fragments -------------------------------------------------------------------------

def test_extract_fragments_basic_and_min_length() -> None:
    ev = "Table 2 proven 'Incoagulable blood (20 WBCT) 38 (69)'; 38/53; 'within 7h' short"
    assert extract_fragments(ev) == ["Incoagulable blood (20 WBCT) 38 (69)"]


def test_extract_fragments_ignores_apostrophes_inside_words() -> None:
    ev = ("CONFLICT: who p.69 'About 50% of bites by ... Russell's vipers'. "
          "Sec 3.4 'Only six bites (2%) occurred within the patient's house'; 6/302")
    assert extract_fragments(ev) == [
        "About 50% of bites by ... Russell's vipers",
        "Only six bites (2%) occurred within the patient's house",
    ]


def test_extract_fragments_none_for_derived_rows() -> None:
    ev = "S1 Appendix Data.xlsx, Snake='IK': 77/101 (derived by src/data/wijayasekara.py)"
    assert extract_fragments(ev) == []


def test_extract_fragments_multiple_and_at_start() -> None:
    ev = "'first detected 30 minutes' / 'between 30 minutes and 13 hours'"
    assert extract_fragments(ev) == ["first detected 30 minutes", "between 30 minutes and 13 hours"]


def test_normalise_dashes_quotes_whitespace() -> None:
    assert normalise("  A–B—C ’x”\n\tY ") == "a-b-c 'x\" y"
    assert compact("Envenom-\ning  (96%)") == "envenoming96"


def test_fragment_parts_split_on_ellipsis() -> None:
    assert fragment_parts("Abdominal pain ... and vomiting… was") == ["abdominalpain", "andvomiting", "was"]


def test_fragment_in_requires_every_part() -> None:
    source = compact("Abdominal pain, often with nausea and vomiting, was reported")
    assert fragment_in("Abdominal pain ... and vomiting", source)
    assert not fragment_in("Abdominal pain ... and fever", source)


# --- bib and sources --------------------------------------------------------------------

def test_parse_bib_fields_with_nested_braces() -> None:
    bib = parse_bib(BIB)
    assert set(bib) == {"alpha2020", "beta2021"}
    assert bib["alpha2020"]["title"] == "A {nested} title"
    assert bib["alpha2020"]["url"].endswith("PMC123/")


def test_mentioned_keys() -> None:
    assert mentioned_keys("CONFLICT: beta2021 p.12 'x'", {"alpha2020", "beta2021"}) == ["beta2021"]


def test_fetch_source_text_pmc_fulltext() -> None:
    fetch = fake_fetch({f"{EUROPEPMC}/PMC123/fullTextXML": ALPHA_XML})
    kind, text = fetch_source_text(parse_bib(BIB)["alpha2020"], fetch)
    assert kind == "fulltext" and "Pain" in text and "<td>" not in text


def test_fetch_source_text_abstract_fallback() -> None:
    record = {"resultList": {"result": [{"abstractText": "<b>There were 5 dry bites (20%).</b>"}]}}
    entry = {"doi": "10.1/x", "url": "https://doi.org/10.1/x"}

    def fetch(url: str) -> bytes | None:
        return json.dumps(record).encode() if url.startswith(f"{EUROPEPMC}/search") else None

    assert fetch_source_text(entry, fetch) == ("abstract", " There were 5 dry bites (20%). ")


def test_source_store_caches_and_offline(tmp_path: Path) -> None:
    bib = parse_bib(BIB)
    fetch = fake_fetch({f"{EUROPEPMC}/PMC123/fullTextXML": ALPHA_XML})
    store = SourceStore(bib, tmp_path, fetch)
    assert store.text("alpha2020") is not None and store.kinds["alpha2020"] == "fulltext"
    assert (tmp_path / "alpha2020.txt").exists()
    offline = SourceStore(bib, tmp_path, None)
    assert offline.text("alpha2020") == store.text("alpha2020")
    assert offline.text("beta2021") is None and offline.kinds["beta2021"] == "unavailable"


# --- statuses ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "args, expected",
    [((0, 0, 1, 0), "no_quote"), ((2, 0, 1, 0), "found"), ((2, 1, 1, 0), "partial"),
     ((2, 2, 1, 0), "not_found"), ((2, 2, 2, 2), "source_unavailable"), ((2, 0, 2, 1), "found")],
)
def test_row_status(args: tuple[int, int, int, int], expected: str) -> None:
    assert row_status(*args) == expected


def _cached_store(tmp_path: Path) -> SourceStore:
    (tmp_path / "alpha2020.txt").write_text("# kind: fulltext\n" + xml_to_text(ALPHA_XML.decode("utf-8")), encoding="utf-8")
    return SourceStore(parse_bib(BIB), tmp_path, None)


def test_check_row_statuses(tmp_path: Path) -> None:
    store = _cached_store(tmp_path)
    found = check_row("t", "i", "alpha2020", "p.459 'first detected 30 minutes to 4-hours' and 'Pain 53 (96)'", store)
    assert found.status == "found" and found.missing == []
    partial = check_row("t", "i", "alpha2020", "'first detected 30 minutes' and 'Pain 99 (100)' x", store)
    assert partial.status == "partial" and partial.missing == ["Pain 99 (100)"]
    assert check_row("t", "i", "alpha2020", "'nothing like this here'", store).status == "not_found"
    assert check_row("t", "i", "alpha2020", "derived 77/101", store).status == "no_quote"
    assert check_row("t", "i", "beta2021", "'some quoted sentence'", store).status == "source_unavailable"


def test_check_row_uses_keys_mentioned_in_evidence(tmp_path: Path) -> None:
    store = _cached_store(tmp_path)
    result = check_row("t", "i", "beta2021", "CONFLICT: alpha2020 'within the patient's house'", store)
    assert result.sources == ["beta2021", "alpha2020"]
    assert result.status == "found" and result.unavailable == ["beta2021"]


def test_check_knowledge_and_render(tmp_path: Path) -> None:
    clinical = [("Species a", "neuro", 0.0, 1.0, 1.0, "alpha2020", "'first detected 30 minutes'", False),
                ("Species b", "haemo", 0.5, 3.0, 1.0, "alpha2020", "'not in the source text'", False)]
    species = [("Species a", "A", "venomous", 0.1, "beta2021", "'There were 5 dry bites'", False),
               ("Species c", "C", "non-venomous", None, "", "", False)]
    kdir = write_knowledge(tmp_path / "knowledge", clinical=clinical, species=species, bib=BIB)
    store = _cached_store(tmp_path)
    results = check_knowledge(kdir, store)
    by_item = {r.item: r.status for r in results}
    assert by_item["Species a / neuro"] == "found"
    assert by_item["Species b / haemo"] == "not_found"
    assert by_item["Species a / dry_bite_rate"] == "source_unavailable"
    assert "Species c / dry_bite_rate" not in by_item  # no evidence: skipped
    md = render(results, store.kinds)
    assert "does **not** replace human verification" in md and "## not_found (1)" in md


def test_main_offline_writes_report(tmp_path: Path) -> None:
    kdir = write_knowledge(tmp_path / "knowledge", bib=BIB)
    out = tmp_path / "quote_check.md"
    main(["--knowledge-dir", str(kdir), "--out", str(out), "--offline", "--cache-dir", str(tmp_path / "c")])
    assert out.read_text(encoding="utf-8").startswith("# Automatic quote check")
