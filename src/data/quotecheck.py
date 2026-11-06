"""Automatic pre-check: do the verbatim quotes in the knowledge tables occur in their sources?

    python -m src.data.quotecheck                 # fetch open-access texts, write docs/quote_check.md
    python -m src.data.quotecheck --offline       # use data/raw/fulltext_cache/ only

For every row of clinical_table.csv, context_table.csv, species.csv and presentation_delay.csv, the text between
single quotes in `evidence` is extracted and searched for in the open-access text of the row's
sources (the `source_key` keys plus any other bib key named in the evidence). Texts come from
Europe PMC (full-text XML, else the abstract) or from plain PDF links via `pdftotext`, and are
cached under data/raw/fulltext_cache/<key>.txt.

This only confirms that the quoted words exist in the source. It does NOT check the numbers
derived from them and does NOT replace human verification: rows stay `verified=false`.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

from src.data.knowledge import split_keys

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = REPO_ROOT / "data" / "raw" / "fulltext_cache"
TABLES: tuple[str, ...] = ("clinical_table.csv", "context_table.csv", "species.csv", "presentation_delay.csv")
MIN_FRAGMENT_CHARS = 12
TIMEOUT_SECONDS = 30
USER_AGENT = "SnakeGuardAI-quotecheck/0.1 (academic research prototype; polite single requests)"
EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
STATUSES: tuple[str, ...] = ("found", "partial", "not_found", "no_quote", "source_unavailable")

Fetcher = Callable[[str], "bytes | None"]

# An opening quote follows start/space/bracket/punctuation; a closing quote is followed by
# space/punctuation/end. Apostrophes inside words ("Russell's", "patient's") match neither.
_QUOTE_RE = re.compile(r"(?<![^\s(\[;:,/])'(.+?)'(?=[\s.,;:)\]/]|$)")
_ELLIPSIS_RE = re.compile(r"\.\.\.|\u2026")
_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"
_QUOTE_CHARS = {"\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u2032": "'",
                "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2033": '"'}


# --- fragments and normalisation -------------------------------------------------------

def extract_fragments(evidence: str, min_chars: int = MIN_FRAGMENT_CHARS) -> list[str]:
    """Verbatim quotes (text between single quotes) in an evidence cell, at least `min_chars` long."""
    found = [m.group(1).strip() for m in _QUOTE_RE.finditer(str(evidence))]
    return [f for f in found if len(f) >= min_chars]


def normalise(text: str) -> str:
    """Lowercase, NFKC, unify dashes and quotes, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.translate({ord(c): "-" for c in _DASHES})
    text = text.translate({ord(k): v for k, v in _QUOTE_CHARS.items()})
    return re.sub(r"\s+", " ", text).strip()


def compact(text: str) -> str:
    """Normalised text with only letters and digits kept (robust to spacing, line-break hyphens)."""
    return re.sub(r"[^a-z0-9]", "", normalise(text))


def fragment_parts(fragment: str) -> list[str]:
    """Split a fragment on '...' ellipses into the parts that must each occur in the source."""
    parts = [compact(p) for p in _ELLIPSIS_RE.split(fragment)]
    return [p for p in parts if p]


def fragment_in(fragment: str, compact_source: str) -> bool:
    """True if every ellipsis-separated part of `fragment` occurs in the compacted source text."""
    parts = fragment_parts(fragment)
    return bool(parts) and all(p in compact_source for p in parts)


# --- bibliography -----------------------------------------------------------------------

def parse_bib(text: str) -> dict[str, dict[str, str]]:
    """Map citation key -> {field: value} for a BibTeX file (brace-delimited values)."""
    entries: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,", text):
        body = _balanced_body(text, match.end())
        entries[match.group(1)] = _parse_fields(body)
    return entries


def _balanced_body(text: str, start: int) -> str:
    depth = 1
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i]
    return text[start:]


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in re.finditer(r"(\w+)\s*=\s*\{", body):
        value = _balanced_body(body, match.end())
        fields.setdefault(match.group(1).lower(), value.strip())
    return fields


def mentioned_keys(evidence: str, bib_keys: set[str]) -> list[str]:
    """Bib keys named inside the evidence text (e.g. a conflicting guideline quoted in passing)."""
    words = set(re.findall(r"[A-Za-z0-9_]+", str(evidence)))
    return sorted(words & bib_keys)


# --- fetching ---------------------------------------------------------------------------

def http_fetch(url: str) -> bytes | None:
    """GET a URL with a timeout and a polite User-Agent; None on any error."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except Exception:  # noqa: BLE001 - any network/HTTP failure just means "unavailable"
        return None


def xml_to_text(xml: str) -> str:
    """Strip tags (as spaces, so table cells stay separated) and unescape entities."""
    return html.unescape(re.sub(r"<[^>]+>", " ", xml))


def pdf_to_text(data: bytes) -> str | None:
    """Convert PDF bytes to text with `pdftotext` if it is installed, else None."""
    exe = shutil.which("pdftotext")
    if exe is None or not data.startswith(b"%PDF"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "source.pdf"
        pdf.write_bytes(data)
        try:
            result = subprocess.run([exe, "-enc", "UTF-8", str(pdf), "-"], capture_output=True,
                                    timeout=120, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
    text = result.stdout.decode("utf-8", errors="replace")
    return text if text.strip() else None


def pmcid_from_url(url: str) -> str | None:
    match = re.search(r"PMC\d+", url or "")
    return match.group(0) if match else None


def europepmc_query(entry: dict[str, str]) -> str | None:
    """Europe PMC search query for an entry: by PubMed id in the URL, else by DOI."""
    med = re.search(r"(?:europepmc\.org/article/MED/|pubmed\.ncbi\.nlm\.nih\.gov/)(\d+)", entry.get("url", ""))
    if med:
        return f"EXT_ID:{med.group(1)} AND SRC:MED"
    if entry.get("doi"):
        return f'DOI:"{entry["doi"]}"'
    return None


def europepmc_record(query: str, fetch: Fetcher) -> dict | None:
    url = f"{EUROPEPMC}/search?" + urllib.parse.urlencode(
        {"query": query, "resultType": "core", "format": "json", "pageSize": 1})
    data = fetch(url)
    if not data:
        return None
    try:
        results = json.loads(data.decode("utf-8")).get("resultList", {}).get("result", [])
    except (ValueError, AttributeError):
        return None
    return results[0] if results else None


def europepmc_fulltext(pmcid: str, fetch: Fetcher) -> str | None:
    data = fetch(f"{EUROPEPMC}/{pmcid}/fullTextXML")
    if not data or b"<article" not in data[:5000]:
        return None
    return xml_to_text(data.decode("utf-8", errors="replace"))


def fetch_source_text(entry: dict[str, str], fetch: Fetcher) -> tuple[str, str] | None:
    """(kind, text) for a bib entry: Europe PMC full text, PDF text, or Europe PMC abstract."""
    url = entry.get("url", "")
    pmcid = pmcid_from_url(url)
    if pmcid and (text := europepmc_fulltext(pmcid, fetch)):
        return "fulltext", text
    if re.search(r"(\.pdf|/content)$", url.split("?")[0], re.IGNORECASE):
        data = fetch(url)
        if data and (text := pdf_to_text(data)):
            return "pdf", text
    query = europepmc_query(entry)
    record = europepmc_record(query, fetch) if query else None
    if record is None:
        return None
    if record.get("pmcid") and record["pmcid"] != pmcid and (text := europepmc_fulltext(record["pmcid"], fetch)):
        return "fulltext", text
    if record.get("abstractText"):
        return "abstract", xml_to_text(record["abstractText"])
    return None


@dataclass
class SourceStore:
    """Source texts by bib key, read from the cache or fetched (and then cached)."""

    bib: dict[str, dict[str, str]]
    cache_dir: Path
    fetch: Fetcher | None = http_fetch  # None = offline (cache only)
    kinds: dict[str, str] = field(default_factory=dict)
    _texts: dict[str, str | None] = field(default_factory=dict)

    def text(self, key: str) -> str | None:
        """Compacted text of a source, or None if unavailable."""
        if key not in self._texts:
            self._texts[key] = self._load(key)
        return self._texts[key]

    def _load(self, key: str) -> str | None:
        path = self.cache_dir / f"{key}.txt"
        if path.exists():
            kind, _, body = path.read_text(encoding="utf-8").partition("\n")
            self.kinds[key] = kind.removeprefix("# kind: ").strip() or "cached"
            return compact(body)
        if self.fetch is None or key not in self.bib:
            self.kinds[key] = "unavailable"
            return None
        got = fetch_source_text(self.bib[key], self.fetch)
        if got is None:
            self.kinds[key] = "unavailable"
            return None
        kind, text = got
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# kind: {kind}\n{text}", encoding="utf-8")
        self.kinds[key] = kind
        return compact(text)


# --- checking ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RowResult:
    table: str
    item: str
    sources: list[str]
    fragments: list[str]
    missing: list[str]
    unavailable: list[str]
    status: str


def row_status(n_fragments: int, n_missing: int, n_sources: int, n_unavailable: int) -> str:
    """Status of one row from its fragment and source counts."""
    if n_fragments == 0:
        return "no_quote"
    if n_unavailable == n_sources:
        return "source_unavailable"
    if n_missing == 0:
        return "found"
    return "partial" if n_missing < n_fragments else "not_found"


def check_row(table: str, item: str, source_key: str, evidence: str, store: SourceStore) -> RowResult:
    """Check every quoted fragment of one row against all of the row's sources."""
    keys = list(dict.fromkeys(split_keys(source_key) + mentioned_keys(evidence, set(store.bib))))
    texts = {k: store.text(k) for k in keys}
    available = [t for t in texts.values() if t is not None]
    unavailable = [k for k, t in texts.items() if t is None]
    fragments = extract_fragments(evidence)
    missing = [f for f in fragments if not any(fragment_in(f, t) for t in available)]
    status = row_status(len(fragments), len(missing), len(keys), len(unavailable))
    return RowResult(table, item, keys, fragments, missing, unavailable, status)


def row_label(table: str, row: dict[str, str]) -> str:
    if table == "presentation_delay.csv":
        return f"{row['profile']} / {row['min_hours']}-{row['max_hours'] or 'open'} h"
    what = "dry_bite_rate" if table == "species.csv" else row[list(row)[1]]
    return f"{row['species']} / {what}"


def knowledge_rows(knowledge_dir: Path) -> list[tuple[str, str, str, str]]:
    """(table, item, source_key, evidence) for every row with evidence text."""
    rows: list[tuple[str, str, str, str]] = []
    for name in TABLES:
        path = knowledge_dir / name
        if not path.exists():
            continue
        table = pd.read_csv(path, dtype=str).fillna("")
        for r in table.to_dict("records"):
            if r.get("evidence", "").strip():
                rows.append((name, row_label(name, r), r.get("source_key", ""), r["evidence"]))
    return rows


def check_knowledge(knowledge_dir: Path, store: SourceStore) -> list[RowResult]:
    return [check_row(t, i, k, e, store) for t, i, k, e in knowledge_rows(knowledge_dir)]


# --- report -----------------------------------------------------------------------------

def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render(results: list[RowResult], kinds: dict[str, str]) -> str:
    counts = {s: sum(r.status == s for r in results) for s in STATUSES}
    lines = [
        "# Automatic quote check",
        "",
        "Generated by `python -m src.data.quotecheck`. **This is an automatic pre-check only.**",
        "It confirms that the text quoted in single quotes in each row's `evidence` occurs in an",
        "open-access copy of one of the row's sources (Europe PMC full text or abstract, or a PDF).",
        "It does **not** check the numbers derived from the quotes, the mapping to symptoms, or the",
        "denominators, and it does **not** replace human verification: rows stay `verified=false`",
        "until a person has checked them against the source.",
        "",
        "Matching ignores case, spacing, punctuation and dash/quote style; a quote with `...` is split",
        "and every part must occur. Quotes shorter than "
        f"{MIN_FRAGMENT_CHARS} characters are ignored. Sources searched are the row's `source_key`",
        "plus any bib key named in the evidence. `abstract` sources only contain the abstract.",
        "",
        "## Summary",
        "",
        "| status | rows |",
        "|---|---|",
        *[f"| {s} | {counts[s]} |" for s in STATUSES],
        f"| **total** | **{len(results)}** |",
        "",
    ]
    for status in STATUSES:
        group = [r for r in results if r.status == status]
        if not group:
            continue
        lines += [f"## {status} ({len(group)})", "", "| table | item | source(s) | fragment(s) missing |",
                  "|---|---|---|---|"]
        for r in group:
            srcs = ", ".join(f"{k} ({kinds.get(k, '?')})" for k in r.sources) or "(none)"
            missing = "; ".join(f"'{m}'" for m in r.missing) or "-"
            lines.append(f"| {r.table} | {_cell(r.item)} | {_cell(srcs)} | {_cell(missing)} |")
        lines.append("")
    lines += ["## Sources", "", "| key | text used |", "|---|---|",
              *[f"| {k} | {v} |" for k, v in sorted(kinds.items())], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--knowledge-dir", default=str(REPO_ROOT / "knowledge"))
    parser.add_argument("--out", default=str(REPO_ROOT / "docs" / "quote_check.md"))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    parser.add_argument("--offline", action="store_true", help="use cached texts only")
    args = parser.parse_args(argv)
    knowledge_dir = Path(args.knowledge_dir)
    bib = parse_bib((knowledge_dir / "sources.bib").read_text(encoding="utf-8"))
    store = SourceStore(bib, Path(args.cache_dir), None if args.offline else http_fetch)
    results = check_knowledge(knowledge_dir, store)
    Path(args.out).write_text(render(results, store.kinds), encoding="utf-8")
    counts = ", ".join(f"{s} {sum(r.status == s for r in results)}" for s in STATUSES)
    print(f"wrote {len(results)} row(s) to {args.out}: {counts}")


if __name__ == "__main__":
    main()
