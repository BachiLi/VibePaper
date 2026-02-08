"""
Export 5-star rated papers to a standalone HTML page.
"""

import json
import html
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
PAPERS_FILE = DATA_DIR / "papers.json"
RATINGS_FILE = DATA_DIR / "ratings.json"
OUTPUT_FILE = Path(__file__).parent / "favorites.html"


def main():
    with open(PAPERS_FILE, "r", encoding="utf-8") as f:
        papers = json.load(f)
    with open(RATINGS_FILE, "r", encoding="utf-8") as f:
        ratings = json.load(f)

    paper_by_key = {p["dblp_key"]: p for p in papers}

    # Collect 5-star papers
    favorites = []
    for key, score in ratings.items():
        if score == 5 and key in paper_by_key:
            favorites.append(paper_by_key[key])

    # Sort by year (oldest first), then title
    favorites.sort(key=lambda p: (p.get("year", 0), p.get("title", "")))

    print(f"Found {len(favorites)} five-star papers")

    # Generate HTML
    cards_html = []
    for p in favorites:
        title = html.escape(p.get("title") or "Untitled")
        authors = ", ".join(html.escape(a) for a in (p.get("authors") or []))
        year = p.get("year", "")
        venue = html.escape(p.get("venue") or "")
        abstract = html.escape(p.get("abstract") or "")
        doi = p.get("doi") or ""

        doi_link = ""
        if doi:
            doi_escaped = html.escape(doi)
            doi_link = f'<a href="https://doi.org/{doi_escaped}" target="_blank">DOI: {doi_escaped}</a>'

        cards_html.append(f"""    <div class="paper">
      <div class="title">{title}</div>
      <div class="authors">{authors}</div>
      <div class="meta">{venue} {year}{f' &middot; {doi_link}' if doi_link else ''}</div>
      <div class="abstract">{abstract}</div>
    </div>""")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VibePaper - Favorite Papers ({len(favorites)})</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
    line-height: 1.6;
  }}
  header {{
    background: #1a1a2e;
    color: #fff;
    padding: 2rem;
    text-align: center;
  }}
  header h1 {{ font-size: 1.8rem; margin-bottom: 0.3rem; }}
  header p {{ opacity: 0.8; font-size: 0.95rem; }}
  .container {{
    max-width: 900px;
    margin: 2rem auto;
    padding: 0 1rem;
  }}
  .paper {{
    background: #fff;
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }}
  .paper:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
  .title {{
    font-size: 1.1rem;
    font-weight: 600;
    color: #1a1a2e;
    margin-bottom: 0.4rem;
  }}
  .authors {{
    font-size: 0.9rem;
    color: #555;
    margin-bottom: 0.3rem;
  }}
  .meta {{
    font-size: 0.85rem;
    color: #777;
    margin-bottom: 0.6rem;
  }}
  .meta a {{ color: #4a6fa5; text-decoration: none; }}
  .meta a:hover {{ text-decoration: underline; }}
  .abstract {{
    font-size: 0.9rem;
    color: #444;
    line-height: 1.7;
  }}
</style>
</head>
<body>
  <header>
    <h1>Favorite Papers</h1>
    <p>{len(favorites)} five-star papers from VibePaper</p>
  </header>
  <div class="container">
{chr(10).join(cards_html)}
  </div>
</body>
</html>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
