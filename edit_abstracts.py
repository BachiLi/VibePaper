#!/usr/bin/env python
"""
Local web interface for manually editing papers without abstracts.
Lets you enter an abstract or remove a paper from the database.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from paper_io import load_papers, save_papers

PORT = 8899


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Edit Missing Abstracts</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #f8f9fa; }
  h1 { color: #333; }
  .stats { background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .paper { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .paper h3 { margin-top: 0; color: #1a1a2e; }
  .meta { color: #666; font-size: 0.9em; margin-bottom: 10px; }
  .meta a { color: #0066cc; }
  textarea { width: 100%%; height: 120px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-family: inherit; font-size: 0.95em; box-sizing: border-box; resize: vertical; }
  .actions { margin-top: 10px; display: flex; gap: 10px; }
  button { padding: 8px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.95em; }
  .save-btn { background: #28a745; color: white; }
  .save-btn:hover { background: #218838; }
  .delete-btn { background: #dc3545; color: white; }
  .delete-btn:hover { background: #c82333; }
  .skip-btn { background: #6c757d; color: white; }
  .skip-btn:hover { background: #5a6268; }
  .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
  .nav { display: flex; gap: 10px; margin-bottom: 20px; }
  .nav a { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
  .nav a:hover { background: #0056b3; }
</style>
</head>
<body>
<h1>Edit Missing Abstracts</h1>
{content}
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress request logs

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        papers = load_papers()
        missing = [(i, p) for i, p in enumerate(papers) if not p.get("abstract")]

        page = int(params.get("page", ["0"])[0])
        per_page = 20
        msg = params.get("msg", [""])[0]

        total = len(missing)
        start = page * per_page
        end = min(start + per_page, total)
        page_items = missing[start:end]

        content = ""
        if msg:
            content += f'<div class="success">{msg}</div>'

        with_abstract = sum(1 for p in papers if p.get("abstract"))
        content += f'<div class="stats">Total papers: {len(papers)} | With abstract: {with_abstract} | Missing: {total}</div>'

        # Pagination
        content += '<div class="nav">'
        if page > 0:
            content += f'<a href="/?page={page-1}">&larr; Prev</a>'
        content += f'<span style="padding:8px">Page {page+1} of {(total + per_page - 1) // per_page} (showing {start+1}-{end} of {total})</span>'
        if end < total:
            content += f'<a href="/?page={page+1}">Next &rarr;</a>'
        content += '</div>'

        for idx, paper in page_items:
            title = paper.get("title", "Unknown")
            authors = ", ".join(paper.get("authors", [])[:3])
            year = paper.get("year", "?")
            venue = paper.get("venue", "?")
            doi = paper.get("doi", "")
            doi_link = f'<a href="https://doi.org/{doi}" target="_blank">{doi}</a>' if doi else "N/A"
            s2_id = paper.get("s2_id", "")
            s2_link = f'<a href="https://www.semanticscholar.org/paper/{s2_id}" target="_blank">S2</a>' if s2_id else ""

            content += f'''
            <div class="paper" id="paper-{idx}">
                <h3>{title}</h3>
                <div class="meta">
                    {authors} ({year}) &mdash; {venue}<br>
                    DOI: {doi_link} {s2_link}
                </div>
                <form method="POST" action="/save">
                    <input type="hidden" name="idx" value="{idx}">
                    <input type="hidden" name="page" value="{page}">
                    <textarea name="abstract" placeholder="Paste abstract here..."></textarea>
                    <div class="actions">
                        <button type="submit" name="action" value="save" class="save-btn">Save Abstract</button>
                        <button type="submit" name="action" value="delete" class="delete-btn"
                            onclick="return confirm('Remove this paper from the database?')">Remove Paper</button>
                    </div>
                </form>
            </div>'''

        html = HTML_TEMPLATE.replace("{content}", content)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        params = parse_qs(body)

        idx = int(params["idx"][0])
        page = params.get("page", ["0"])[0]
        action = params["action"][0]

        papers = load_papers()

        if action == "save":
            abstract = params.get("abstract", [""])[0].strip()
            if abstract:
                papers[idx]["abstract"] = abstract
                papers[idx]["abstract_source"] = "manual"
                save_papers(papers)
                msg = f"Saved abstract for: {papers[idx].get('title', '?')}"
            else:
                msg = "No abstract provided, skipped."
        elif action == "delete":
            title = papers[idx].get("title", "?")
            papers.pop(idx)
            save_papers(papers)
            msg = f"Removed paper: {title}"

        self.send_response(303)
        self.send_header("Location", f"/?page={page}&msg={msg}")
        self.end_headers()


if __name__ == "__main__":
    from paper_io import DATA_FILE

    print(f"Starting server at http://localhost:{PORT}")
    print(f"Data file: {DATA_FILE}")
    papers = load_papers()
    missing = sum(1 for p in papers if not p.get("abstract"))
    print(f"Papers missing abstracts: {missing}")
    server = HTTPServer(("localhost", PORT), Handler)
    server.serve_forever()
