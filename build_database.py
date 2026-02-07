#!/usr/bin/env python
"""
Build the paper database from scratch.

This script:
1. Fetches TOG papers from DBLP
2. Fetches SIGGRAPH/SIGGRAPH Asia conference track papers (2022+)
3. Fetches older SIGGRAPH papers (1985-2001)
4. Merges all sources (deduplicating by DOI and DBLP key)
5. Enriches with abstracts from Semantic Scholar
6. Fills missing abstracts from OpenAlex

Output: data/all_papers_enriched.json
"""

import json
import re
import time
import urllib.request
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent / "data"
DBLP_API = "https://dblp.org/search/publ/api"
S2_BATCH_API = "https://api.semanticscholar.org/graph/v1/paper/batch"
OPENALEX_API = "https://api.openalex.org/works"


def fetch_tog_papers() -> list[dict]:
    """Fetch all TOG (Transactions on Graphics) papers from DBLP."""
    print("\n=== Fetching TOG papers ===")
    all_papers = []
    offset = 0
    batch_size = 1000

    while True:
        url = f"{DBLP_API}?q=stream:streams/journals/tog:&format=json&h={batch_size}&f={offset}"
        print(f"  Fetching offset {offset}...")

        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"  Error: {e}")
            break

        hits = data["result"]["hits"].get("hit", [])
        if not hits:
            break

        for hit in hits:
            info = hit["info"]
            authors_data = info.get("authors", {}).get("author", [])
            if isinstance(authors_data, dict):
                authors_data = [authors_data]
            authors = [a.get("text", a) if isinstance(a, dict) else a for a in authors_data]

            paper = {
                "dblp_key": info.get("key"),
                "title": info.get("title"),
                "authors": authors,
                "venue": info.get("venue"),
                "year": int(info.get("year", 0)),
                "doi": info.get("doi"),
                "url": info.get("ee"),
                "type": "tog",
            }
            all_papers.append(paper)

        offset += len(hits)
        time.sleep(0.3)

    print(f"  Total TOG papers: {len(all_papers)}")
    return all_papers


def is_conference_paper(info: dict) -> bool:
    """Check if a paper is a conference track paper (not journal)."""
    venue = info.get("venue", "")
    pages = info.get("pages", "")
    paper_type = info.get("type", "")

    if venue not in ("SIGGRAPH", "SIGGRAPH Asia"):
        return False
    if paper_type not in ("Conference and Workshop Papers", ""):
        return False

    # Conference papers have page numbers like "21:1-21:9" or "53-59" or just "73"
    if pages:
        pages_str = str(pages)
        if re.match(r"^\d+:\d+-\d+:\d+$", pages_str):  # Article format: 21:1-21:9
            return True
        if re.match(r"^\d+-\d+$", pages_str):  # Page range: 53-59
            return True
        if re.match(r"^\d+$", pages_str):  # Single number: 73
            return True

    return False


def fetch_siggraph_conf_papers() -> list[dict]:
    """Fetch SIGGRAPH/SIGGRAPH Asia conference track papers (2022+)."""
    print("\n=== Fetching conference track papers ===")
    all_papers = []

    for venue in ["siggraph", "siggrapha"]:
        for year in range(2022, 2030):
            url = f"{DBLP_API}?q=streamid:conf/{venue}:+year:{year}:&format=json&h=500"

            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    data = json.loads(resp.read().decode())
            except Exception as e:
                print(f"  Error fetching {venue} {year}: {e}")
                continue

            papers = []
            for hit in data["result"]["hits"].get("hit", []):
                info = hit["info"]
                if not is_conference_paper(info):
                    continue

                authors_data = info.get("authors", {}).get("author", [])
                if isinstance(authors_data, dict):
                    authors_data = [authors_data]
                authors = [a.get("text", a) if isinstance(a, dict) else a for a in authors_data]

                paper = {
                    "dblp_key": info.get("key"),
                    "title": info.get("title"),
                    "authors": authors,
                    "venue": info.get("venue"),
                    "year": int(info.get("year", 0)),
                    "pages": info.get("pages"),
                    "doi": info.get("doi"),
                    "url": info.get("ee"),
                    "type": "conf_track",
                }
                papers.append(paper)

            if papers:
                venue_name = "SIGGRAPH" if venue == "siggraph" else "SIGGRAPH Asia"
                print(f"  {venue_name} {year}: {len(papers)} papers")
                all_papers.extend(papers)

            time.sleep(0.3)

    print(f"  Total conference track papers: {len(all_papers)}")
    return all_papers


def is_old_technical_paper(info: dict) -> bool:
    """Check if a paper is a main technical paper (for older SIGGRAPH)."""
    venue = info.get("venue", "")
    pages = info.get("pages", "")
    paper_type = info.get("type", "")

    if venue != "SIGGRAPH":
        return False
    if paper_type not in ("Conference and Workshop Papers", ""):
        return False
    if pages and re.match(r"^\d+-\d+$", str(pages)):
        return True
    return False


def fetch_old_siggraph_papers() -> list[dict]:
    """Fetch older SIGGRAPH papers (1985-2001)."""
    print("\n=== Fetching older SIGGRAPH papers (1985-2001) ===")
    all_papers = []

    for year in range(1985, 2002):
        url = f"{DBLP_API}?q=streamid:conf/siggraph:+year:{year}:&format=json&h=500"

        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"  Error fetching {year}: {e}")
            continue

        papers = []
        for hit in data["result"]["hits"].get("hit", []):
            info = hit["info"]
            if not is_old_technical_paper(info):
                continue

            authors_data = info.get("authors", {}).get("author", [])
            if isinstance(authors_data, dict):
                authors_data = [authors_data]
            authors = [a.get("text", a) if isinstance(a, dict) else a for a in authors_data]

            paper = {
                "dblp_key": info.get("key"),
                "title": info.get("title"),
                "authors": authors,
                "venue": "SIGGRAPH",
                "year": int(info.get("year", 0)),
                "pages": info.get("pages"),
                "doi": info.get("doi"),
                "url": info.get("ee"),
                "type": "old_siggraph",
            }
            papers.append(paper)

        if papers:
            print(f"  SIGGRAPH {year}: {len(papers)} papers")
        all_papers.extend(papers)
        time.sleep(0.3)

    print(f"  Total older SIGGRAPH papers: {len(all_papers)}")
    return all_papers


def merge_papers(tog: list, conf: list, old: list) -> list[dict]:
    """Merge paper lists, removing duplicates."""
    print("\n=== Merging papers ===")
    all_dois = set()
    all_keys = set()
    merged = []

    # Start with TOG papers
    for p in tog:
        doi = p.get("doi")
        key = p.get("dblp_key")
        if doi:
            all_dois.add(doi.lower())
        if key:
            all_keys.add(key)
        merged.append(p)

    # Add conference track papers
    conf_added = 0
    for p in conf:
        doi = p.get("doi")
        key = p.get("dblp_key")
        if doi and doi.lower() in all_dois:
            continue
        if key and key in all_keys:
            continue
        if doi:
            all_dois.add(doi.lower())
        if key:
            all_keys.add(key)
        merged.append(p)
        conf_added += 1

    # Add older SIGGRAPH papers
    old_added = 0
    for p in old:
        doi = p.get("doi")
        key = p.get("dblp_key")
        if doi and doi.lower() in all_dois:
            continue
        if key and key in all_keys:
            continue
        if doi:
            all_dois.add(doi.lower())
        if key:
            all_keys.add(key)
        merged.append(p)
        old_added += 1

    print(f"  TOG papers: {len(tog)}")
    print(f"  Conference track added: {conf_added}")
    print(f"  Older SIGGRAPH added: {old_added}")
    print(f"  Total merged: {len(merged)}")
    return merged


def enrich_with_semantic_scholar(papers: list[dict], batch_size: int = 100) -> list[dict]:
    """Enrich papers with abstracts from Semantic Scholar."""
    print("\n=== Enriching with Semantic Scholar abstracts ===")

    papers_with_doi = [(i, p) for i, p in enumerate(papers) if p.get("doi")]
    print(f"  Papers with DOI: {len(papers_with_doi)}")

    total_found = 0
    for batch_start in range(0, len(papers_with_doi), batch_size):
        batch = papers_with_doi[batch_start:batch_start + batch_size]
        dois = [p["doi"] for _, p in batch]

        print(f"  Batch {batch_start // batch_size + 1}/{(len(papers_with_doi) + batch_size - 1) // batch_size}...", end=" ", flush=True)

        try:
            response = requests.post(
                S2_BATCH_API,
                params={"fields": "title,abstract,citationCount,year,paperId,externalIds"},
                json={"ids": [f"DOI:{doi}" for doi in dois]},
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                doi_to_data = {}
                for item in results:
                    if item is not None:
                        ext_ids = item.get("externalIds", {})
                        doi = ext_ids.get("DOI")
                        if doi:
                            doi_to_data[doi.lower()] = item

                found = 0
                for idx, paper in batch:
                    doi_lower = paper["doi"].lower()
                    if doi_lower in doi_to_data:
                        data = doi_to_data[doi_lower]
                        papers[idx]["abstract"] = data.get("abstract")
                        papers[idx]["s2_id"] = data.get("paperId")
                        papers[idx]["citation_count"] = data.get("citationCount")
                        if data.get("abstract"):
                            found += 1

                total_found += found
                print(f"found {found}")

            elif response.status_code == 429:
                print("rate limited, waiting 60s...")
                time.sleep(60)
                continue
            else:
                print(f"error {response.status_code}")

        except requests.RequestException as e:
            print(f"error: {e}")

        time.sleep(1)

    print(f"  Total abstracts from Semantic Scholar: {total_found}")
    return papers


def reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    words = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words.keys()))


def clean_abstract(text: str) -> str:
    """Remove copyright boilerplate from abstract."""
    patterns = [
        r"^.*?Permission to make digital or hard copies.*?(?:Abstract|ABSTRACT)\s*",
        r"^.*?©\s*\d{4}\s*ACM.*?(?:Abstract|ABSTRACT)\s*",
        r"^.*?Request permissions from.*?(?:Abstract|ABSTRACT)\s*",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*#.*?(?:Abstract|ABSTRACT)\s*", "", text, flags=re.DOTALL)
    return text.strip()


def is_valid_abstract(text: str) -> bool:
    """Check if abstract is real content, not page metadata."""
    if not text or len(text) < 50:
        return False

    # Bad patterns that indicate scraped page metadata instead of abstract
    bad_patterns = [
        "article ",  # Starts with "article " (page navigation)
        "Authors Info",
        "View Profile",
        "Share on",
        "ACM Transactions on Graphics",
        "ACM SIGGRAPH",
        "Info & Claims",
        "Citations",
        "Downloads",
        "Publication History",
    ]

    text_start = text[:300].lower()
    for pattern in bad_patterns:
        if pattern.lower() in text_start:
            return False

    return True


def enrich_with_openalex(papers: list[dict]) -> list[dict]:
    """Enrich papers with missing abstracts from OpenAlex."""
    print("\n=== Enriching with OpenAlex abstracts ===")

    missing = [(i, p) for i, p in enumerate(papers) if not p.get("abstract") and p.get("doi")]
    print(f"  Papers missing abstracts (with DOI): {len(missing)}")

    found = 0
    for idx, (paper_idx, paper) in enumerate(missing):
        doi = paper["doi"]

        if idx % 100 == 0 and idx > 0:
            print(f"  Progress: {idx}/{len(missing)} (found: {found})", flush=True)

        try:
            resp = requests.get(f"{OPENALEX_API}/doi:{doi}", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                inv_idx = data.get("abstract_inverted_index")
                if inv_idx:
                    abstract = clean_abstract(reconstruct_abstract(inv_idx))
                    if is_valid_abstract(abstract):
                        papers[paper_idx]["abstract"] = abstract
                        papers[paper_idx]["abstract_source"] = "openalex"
                        found += 1
            elif resp.status_code == 429:
                print("  Rate limited, waiting 10s...")
                time.sleep(10)
        except requests.RequestException:
            pass

        time.sleep(0.12)

    print(f"  Total abstracts from OpenAlex: {found}")
    return papers


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Building Paper Database")
    print("=" * 60)

    # Fetch papers from all sources
    tog_papers = fetch_tog_papers()
    conf_papers = fetch_siggraph_conf_papers()
    old_papers = fetch_old_siggraph_papers()

    # Merge
    papers = merge_papers(tog_papers, conf_papers, old_papers)

    # Save intermediate result
    with open(DATA_DIR / "all_papers.json", "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    print(f"\nSaved intermediate to {DATA_DIR / 'all_papers.json'}")

    # Enrich with abstracts
    papers = enrich_with_semantic_scholar(papers)
    papers = enrich_with_openalex(papers)

    # Save final result
    output_file = DATA_DIR / "all_papers_enriched.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    # Final stats
    with_abstract = sum(1 for p in papers if p.get("abstract"))
    print("\n" + "=" * 60)
    print("Database Build Complete")
    print("=" * 60)
    print(f"Total papers: {len(papers)}")
    print(f"Papers with abstracts: {with_abstract} ({100 * with_abstract / len(papers):.1f}%)")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
