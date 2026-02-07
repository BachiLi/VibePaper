#!/usr/bin/env python
"""
Fetch abstracts from SIGGRAPH History Archive for older papers.
https://history.siggraph.org/
"""

import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent / "data"
INPUT_FILE = DATA_DIR / "all_papers_enriched.json"
OUTPUT_FILE = INPUT_FILE

SITEMAP_BASE = "https://history.siggraph.org/wp-sitemap-posts-learning-{}.xml"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def normalize_title(title: str) -> str:
    """Normalize title for matching."""
    # Remove punctuation, lowercase, normalize whitespace
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def fetch_all_history_urls() -> dict[str, str]:
    """Fetch all URLs from SIGGRAPH History sitemap and index by normalized title."""
    print("Fetching SIGGRAPH History sitemap...")
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    url_map = {}
    for i in range(1, 9):
        url = SITEMAP_BASE.format(i)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                for loc in root.findall(".//sm:loc", ns):
                    page_url = loc.text
                    # Extract title from URL slug
                    match = re.search(r"/learning/(.+?)(?:-by-|-chaired-by-|/$)", page_url)
                    if match:
                        slug = match.group(1).replace("-", " ")
                        normalized = normalize_title(slug)
                        url_map[normalized] = page_url
        except Exception as e:
            print(f"  Error fetching sitemap {i}: {e}")
        time.sleep(0.2)

    print(f"  Found {len(url_map)} pages")
    return url_map


def fetch_abstract_from_page(url: str) -> str | None:
    """Fetch and extract abstract from a SIGGRAPH History page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")

            # The abstract is typically in the first <p> tag in the content
            paragraphs = soup.find_all("p")
            for p in paragraphs[:3]:
                text = p.get_text(strip=True)
                # Skip if too short or looks like metadata
                if len(text) > 100 and not text.startswith("1.") and "copyright" not in text.lower():
                    return text
        # 404 is expected for non-existent pages - don't log
    except requests.exceptions.Timeout:
        pass
    except Exception as e:
        print(f"  Error fetching {url}: {e}")

    return None


def generate_url_from_paper(paper: dict) -> str | None:
    """Generate a SIGGRAPH History URL from paper metadata."""
    title = paper.get("title", "")
    authors = paper.get("authors", [])

    if not title or not authors:
        return None

    # Slugify title
    title_slug = title.lower()
    title_slug = re.sub(r"[^\w\s]", "", title_slug)
    title_slug = re.sub(r"\s+", "-", title_slug).strip("-")

    # Get last names of first two authors
    def get_last_name(name):
        parts = name.split()
        return parts[-1].lower() if parts else ""

    if len(authors) == 1:
        author_slug = get_last_name(authors[0])
    elif len(authors) == 2:
        author_slug = f"{get_last_name(authors[0])}-and-{get_last_name(authors[1])}"
    else:
        author_slug = f"{get_last_name(authors[0])}-et-al"

    author_slug = re.sub(r"[^\w-]", "", author_slug)

    return f"https://history.siggraph.org/learning/{title_slug}-by-{author_slug}/"


def match_paper_to_url(paper: dict, url_map: dict[str, str]) -> str | None:
    """Try to match a paper to a SIGGRAPH History URL."""
    title = paper.get("title", "")
    if not title:
        return None

    normalized = normalize_title(title)

    # Exact match from sitemap
    if normalized in url_map:
        return url_map[normalized]

    # Try without trailing period
    if normalized.endswith(" "):
        normalized = normalized.rstrip()
    if normalized in url_map:
        return url_map[normalized]

    # Try partial match (title might be truncated in URL)
    for slug, url in url_map.items():
        if normalized.startswith(slug) or slug.startswith(normalized):
            if len(slug) > 20 and len(normalized) > 20:
                return url

    # Try generating URL from metadata
    generated = generate_url_from_paper(paper)
    return generated


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        papers = json.load(f)

    # Find papers missing abstracts (focus on older ones)
    missing = [(i, p) for i, p in enumerate(papers) if not p.get("abstract")]
    print(f"Papers missing abstracts: {len(missing)}")

    # Fetch URL map
    url_map = fetch_all_history_urls()

    # Try to match and fetch
    found = 0
    for idx, (paper_idx, paper) in enumerate(missing):
        url = match_paper_to_url(paper, url_map)
        if url:
            abstract = fetch_abstract_from_page(url)
            if abstract:
                papers[paper_idx]["abstract"] = abstract
                papers[paper_idx]["abstract_source"] = "siggraph_history"
                found += 1
                if found <= 5:
                    title = paper["title"][:50]
                    print(f"  Found: {title}...")
            time.sleep(0.3)  # Rate limit

        if idx % 100 == 0 and idx > 0:
            print(f"  Progress: {idx}/{len(missing)} (found: {found})")

    print(f"\nFetched {found} abstracts from SIGGRAPH History")

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    with_abstract = sum(1 for p in papers if p.get("abstract"))
    print(f"Papers with abstracts: {with_abstract}/{len(papers)} ({100 * with_abstract / len(papers):.1f}%)")


if __name__ == "__main__":
    main()
