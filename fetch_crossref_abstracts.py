#!/usr/bin/env python
"""
Fetch abstracts from the Crossref API using paper DOIs.
"""

import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
INPUT_FILE = DATA_DIR / "all_papers_enriched.json"
OUTPUT_FILE = INPUT_FILE

CROSSREF_API = "https://api.crossref.org/works"
# Polite pool: include contact email for faster rate limits
HEADERS = {"User-Agent": "PaperRec/1.0 (mailto:paper-rec@example.com)"}


def clean_jats_abstract(raw: str) -> str:
    """Strip JATS XML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_abstract_from_crossref(doi: str) -> str | None:
    """Fetch abstract for a DOI from Crossref. Returns cleaned text or None."""
    url = f"{CROSSREF_API}/{doi}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        raw = data.get("message", {}).get("abstract")
        if raw:
            cleaned = clean_jats_abstract(raw)
            if len(cleaned) > 50:
                return cleaned
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f"    HTTP {e.code} for {doi}", flush=True)
    except Exception as e:
        print(f"    Error for {doi}: {e}", flush=True)
    return None


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        papers = json.load(f)

    candidates = [
        (i, p) for i, p in enumerate(papers) if p.get("doi") and not p.get("abstract")
    ]
    print(f"Papers with DOI but no abstract: {len(candidates)}")

    found = 0

    for idx, (paper_idx, paper) in enumerate(candidates):
        doi = paper["doi"]
        title = paper.get("title", "Unknown")[:60]
        print(f"[{idx+1}/{len(candidates)}] {title}...", flush=True)

        abstract = fetch_abstract_from_crossref(doi)
        if abstract:
            papers[paper_idx]["abstract"] = abstract
            papers[paper_idx]["abstract_source"] = "crossref"
            found += 1
            print(f"  -> FOUND ({len(abstract)} chars)", flush=True)

        # Checkpoint every 50
        if idx % 50 == 0 and idx > 0:
            print(
                f"  === Checkpoint: {idx}/{len(candidates)} (found: {found}) ===",
                flush=True,
            )
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(papers, f, ensure_ascii=False)

        # Crossref polite pool: ~50 req/s allowed with contact info, but be gentle
        time.sleep(0.2)

    # Final save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False)

    print(f"\nFetched {found} abstracts from Crossref")

    with_abstract = sum(1 for p in papers if p.get("abstract"))
    print(
        f"Papers with abstracts: {with_abstract}/{len(papers)}"
        f" ({100 * with_abstract / len(papers):.1f}%)"
    )


if __name__ == "__main__":
    main()
