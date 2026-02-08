#!/usr/bin/env python
"""
Fetch abstracts from Semantic Scholar using Playwright headless browser.
This bypasses API restrictions by scraping the web page directly.
"""

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from paper_io import load_papers, save_papers, DATA_FILE

DATA_DIR = Path(__file__).parent / "data"
INPUT_FILE = DATA_FILE
OUTPUT_FILE = INPUT_FILE

S2_BASE_URL = "https://www.semanticscholar.org/paper"


def fetch_abstract_from_s2(page, s2_id: str, verbose: bool = False) -> str | None:
    """Fetch abstract from Semantic Scholar page using Playwright."""
    url = f"{S2_BASE_URL}/{s2_id}"

    try:
        if verbose:
            print(f"    Loading {url}...", flush=True)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)  # Wait for JS to render

        # Check for bot detection
        if "Human Verification" in page.content():
            print(f"    Bot detected! Waiting 30s...", flush=True)
            time.sleep(30)
            return None

        # Try to click "Expand" button within the paper's abstract section
        abstract_section = page.query_selector(
            ".paper-detail-page__tldr-abstract"
        )
        if abstract_section:
            expand_btn = abstract_section.query_selector('button:has-text("Expand")')
            if expand_btn:
                if verbose:
                    print(f"    Clicking Expand button...", flush=True)
                try:
                    expand_btn.click()
                    time.sleep(0.5)
                except:
                    pass

        # Try different selectors for abstract
        selectors = [
            ".paper-detail-page__tldr-abstract",
            ".cl-paper-abstract",
            '[data-test-id="paper-abstract"]',
        ]

        for selector in selectors:
            abstract_el = page.query_selector(selector)
            if abstract_el:
                text = abstract_el.inner_text().strip()
                # Clean up UI text artifacts
                for label in ("TLDR", "Expand", "Collapse"):
                    text = text.replace(label, "")
                text = text.strip()
                if verbose:
                    print(f"    Found text ({len(text)} chars): {text[:80]}...", flush=True)
                # Skip truncated text (ends with ellipsis)
                if text.endswith("…"):
                    if verbose:
                        print(f"    Skipping truncated text", flush=True)
                    continue
                if text and len(text) > 100:
                    return text

    except PlaywrightTimeout:
        print(f"    Timeout for {s2_id}", flush=True)
    except Exception as e:
        print(f"    Error for {s2_id}: {e}", flush=True)

    return None


BATCH_SIZE = 7  # Restart browser session every N requests to avoid bot detection


def new_browser_page(pw):
    """Create a fresh browser context and page."""
    browser = pw.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="en-US",
    )
    page = context.new_page()
    page.add_init_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined});')
    return browser, page


def main():
    papers = load_papers()

    # Find papers with S2 ID but no abstract
    candidates = [(i, p) for i, p in enumerate(papers) if p.get("s2_id") and not p.get("abstract")]
    print(f"Papers with S2 ID but no abstract: {len(candidates)}")

    found = 0

    with sync_playwright() as pw:
        browser, page = new_browser_page(pw)
        session_count = 0

        for idx, (paper_idx, paper) in enumerate(candidates):
            # Rotate browser session every BATCH_SIZE requests
            if session_count >= BATCH_SIZE:
                browser.close()
                print(f"  --- Rotating browser session (30s cooldown) ---", flush=True)
                time.sleep(30)
                browser, page = new_browser_page(pw)
                session_count = 0

            s2_id = paper["s2_id"]
            title = paper.get("title", "Unknown")[:60]
            print(f"[{idx+1}/{len(candidates)}] {title}...", flush=True)

            abstract = fetch_abstract_from_s2(page, s2_id, verbose=True)
            if abstract:
                papers[paper_idx]["abstract"] = abstract
                papers[paper_idx]["abstract_source"] = "semantic_scholar_web"
                found += 1
                print(f"  -> FOUND abstract ({len(abstract)} chars)", flush=True)
            else:
                print(f"  -> No abstract found", flush=True)

            session_count += 1

            if idx % 5 == 0 and idx > 0:
                print(f"  === Checkpoint: {idx}/{len(candidates)} (found: {found}) ===", flush=True)
                save_papers(papers)

            # Delay between requests
            time.sleep(5)

        browser.close()

    # Final save
    save_papers(papers)

    print(f"\nFetched {found} abstracts from Semantic Scholar")

    with_abstract = sum(1 for p in papers if p.get("abstract"))
    print(f"Papers with abstracts: {with_abstract}/{len(papers)} ({100 * with_abstract / len(papers):.1f}%)")


if __name__ == "__main__":
    main()
