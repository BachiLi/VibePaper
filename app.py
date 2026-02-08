"""
Web interface for the paper recommender.
"""

from flask import Flask, render_template_string, request, jsonify
from recommender import PaperRecommender

app = Flask(__name__)
rec = PaperRecommender()

# Load data on startup
rec.load_papers()
rec.load_embeddings()
rec.load_ratings()
rec.load_readlist()

# Validate embeddings match papers
if rec.embeddings is not None and len(rec.papers) != rec.embeddings.shape[0]:
    print(
        f"\nERROR: Paper count ({len(rec.papers)}) does not match "
        f"embeddings count ({rec.embeddings.shape[0]})."
    )
    print("Please rebuild embeddings: uv run python build.py embeddings\n")
    raise SystemExit(1)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Paper Recommender</title>
    <style>
        :root {
            --bg-primary: #f5f5f5;
            --bg-secondary: #fff;
            --bg-tertiary: #fafafa;
            --bg-hover: #f0f0f0;
            --bg-input: #fff;
            --bg-stats: #e9ecef;
            --bg-abstract: #f8f9fa;
            --text-primary: #333;
            --text-secondary: #666;
            --text-muted: #888;
            --text-abstract: #555;
            --border-color: #ddd;
            --border-input: #ccc;
            --tab-bg: #ddd;
            --btn-bg: #fff;
            --flash-bg: #d4edda;
        }
        .dark {
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-tertiary: #1f2940;
            --bg-hover: #253554;
            --bg-input: #1f2940;
            --bg-stats: #1f2940;
            --bg-abstract: #253554;
            --text-primary: #e8e8e8;
            --text-secondary: #b0b0b0;
            --text-muted: #888;
            --text-abstract: #c0c0c0;
            --border-color: #3a4a6b;
            --border-input: #3a4a6b;
            --tab-bg: #253554;
            --btn-bg: #1f2940;
            --flash-bg: #1e4a3a;
        }
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: var(--bg-primary);
            color: var(--text-primary);
            transition: background 0.3s, color 0.3s;
        }
        h1 { color: var(--text-primary); }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .theme-toggle {
            padding: 8px 16px;
            border: 1px solid var(--border-color);
            background: var(--btn-bg);
            color: var(--text-primary);
            cursor: pointer;
            border-radius: 5px;
            font-size: 14px;
        }
        .theme-toggle:hover { opacity: 0.8; }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            background: var(--tab-bg);
            color: var(--text-primary);
            border: none;
            cursor: pointer;
            border-radius: 5px 5px 0 0;
            font-size: 16px;
        }
        .tab.active { background: var(--bg-secondary); font-weight: bold; }
        .panel {
            display: none;
            background: var(--bg-secondary);
            padding: 20px;
            border-radius: 0 5px 5px 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .panel.active { display: block; }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .search-box input {
            flex: 1;
            padding: 10px;
            font-size: 16px;
            border: 1px solid var(--border-input);
            border-radius: 5px;
            background: var(--bg-input);
            color: var(--text-primary);
        }
        .search-box button {
            padding: 10px 20px;
            font-size: 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .paper {
            border: 1px solid var(--border-color);
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            background: var(--bg-tertiary);
        }
        .paper:hover { background: var(--bg-hover); }
        .paper-title {
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: 5px;
        }
        .paper-meta {
            color: var(--text-secondary);
            font-size: 14px;
            margin-bottom: 10px;
        }
        .paper-authors {
            color: var(--text-muted);
            font-size: 13px;
            margin-bottom: 10px;
        }
        .paper-abstract {
            font-size: 13px;
            color: var(--text-abstract);
            margin-bottom: 10px;
            padding: 8px 10px;
            background: var(--bg-abstract);
            border-left: 3px solid #007bff;
            line-height: 1.5;
            max-height: 100px;
            overflow-y: auto;
        }
        .rating-buttons {
            display: flex;
            gap: 5px;
            align-items: center;
            flex-wrap: wrap;
        }
        .rating-buttons button {
            padding: 5px 12px;
            border: 1px solid var(--border-input);
            background: var(--btn-bg);
            color: var(--text-primary);
            cursor: pointer;
            border-radius: 3px;
        }
        .rating-buttons button:hover { background: var(--bg-hover); }
        .rating-buttons button.selected { background: #007bff; color: white; border-color: #007bff; }
        .rating-buttons button.irrelevant { color: #dc3545; }
        .rating-buttons button.irrelevant.selected { background: #dc3545; color: white; border-color: #dc3545; }
        .score {
            font-weight: bold;
            color: #28a745;
            margin-left: 10px;
        }
        .paper.just-rated {
            animation: rated-flash 0.5s ease;
        }
        @keyframes rated-flash {
            0% { background: var(--flash-bg); }
            100% { background: var(--bg-tertiary); }
        }
        .paper.rated-irrelevant {
            opacity: 0.5;
            transition: opacity 0.3s ease;
        }
        .clear-btn {
            padding: 3px 8px;
            border: 1px solid #999;
            background: var(--btn-bg);
            color: #999;
            cursor: pointer;
            border-radius: 3px;
            margin-left: 5px;
            font-size: 14px;
        }
        .clear-btn:hover { background: #f8d7da; color: #dc3545; border-color: #dc3545; }
        .readlist-btn {
            padding: 5px 12px;
            border: 1px solid #17a2b8;
            background: var(--btn-bg);
            color: #17a2b8;
            cursor: pointer;
            border-radius: 3px;
            margin-left: 10px;
        }
        .readlist-btn:hover { background: var(--bg-hover); }
        .readlist-btn.in-readlist {
            background: #17a2b8;
            color: white;
        }
        .readlist-btn.in-readlist:hover { background: #138496; }
        .rank-control {
            display: inline-flex;
            gap: 3px;
            align-items: center;
            margin-left: 10px;
        }
        .rank-control .rank-label {
            font-size: 12px;
            color: var(--text-muted);
            margin-right: 2px;
            font-weight: bold;
        }
        .rank-control button {
            padding: 3px 10px;
            border: 1px solid #e8a020;
            background: var(--btn-bg);
            color: #e8a020;
            cursor: pointer;
            border-radius: 3px;
            font-size: 14px;
            font-weight: bold;
        }
        .rank-control button:hover { background: #e8a020; color: white; }
        .rec-score {
            background: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
            margin-right: 10px;
        }
        .stats {
            background: var(--bg-stats);
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            color: var(--text-secondary);
        }
        .no-results {
            color: var(--text-secondary);
            font-style: italic;
            padding: 20px;
            text-align: center;
        }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .sort-control {
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sort-control label {
            color: var(--text-secondary);
        }
        .sort-control select {
            padding: 8px 12px;
            border: 1px solid var(--border-input);
            border-radius: 5px;
            background: var(--bg-input);
            color: var(--text-primary);
            font-size: 14px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Paper Recommender</h1>
        <button class="theme-toggle" onclick="toggleTheme()">🌙 Dark Mode</button>
    </div>

    <div class="stats" id="stats">
        Loading stats...
    </div>

    <div class="tabs">
        <button class="tab active" onclick="showTab('search')">Search Papers</button>
        <button class="tab" onclick="showTab('recommendations')">Recommendations</button>
        <button class="tab" onclick="showTab('rated')">My Ratings</button>
        <button class="tab" onclick="showTab('readlist')">Read Later</button>
    </div>

    <div id="search" class="panel active">
        <div class="search-box">
            <input type="text" id="searchQuery" placeholder="Search by title or author..." onkeypress="if(event.key==='Enter')search()">
            <button onclick="search()">Search</button>
        </div>
        <div class="sort-control" id="searchSortControl" style="display:none">
            <label>Sort by:</label>
            <select id="searchSort" onchange="renderSearchResults()">
                <option value="relevance">Relevance</option>
                <option value="year">Year (newest first)</option>
                <option value="year-asc">Year (oldest first)</option>
            </select>
        </div>
        <div id="searchResults"></div>
    </div>

    <div id="recommendations" class="panel">
        <button onclick="getRecommendations()" style="margin-bottom:15px;padding:10px 20px;font-size:16px;background:#28a745;color:white;border:none;border-radius:5px;cursor:pointer;">
            Get Recommendations
        </button>
        <div id="recResults"></div>
    </div>

    <div id="rated" class="panel">
        <div class="sort-control">
            <label>Sort by:</label>
            <select id="ratedSort" onchange="loadRated()">
                <option value="rating">Rating (highest first)</option>
                <option value="year">Year (newest first)</option>
                <option value="year-asc">Year (oldest first)</option>
            </select>
        </div>
        <div id="ratedPapers"></div>
    </div>

    <div id="readlist" class="panel">
        <div class="sort-control">
            <label>Sort by:</label>
            <select id="readlistSort" onchange="loadReadlist()">
                <option value="rank">Rank</option>
                <option value="relevance">Relevance (highest first)</option>
                <option value="year">Year (newest first)</option>
                <option value="year-asc">Year (oldest first)</option>
            </select>
        </div>
        <div id="readlistPapers"></div>
    </div>

    <script>
        let ratings = {};
        let readlist = new Map();
        let totalPapers = 0;
        let cachedSearchPapers = [];
        function escapeHtml(str) {
            if (str == null) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function showTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelector(`.tab[onclick="showTab('${name}')"]`).classList.add('active');
            document.getElementById(name).classList.add('active');

            if (name === 'rated') loadRated();
            if (name === 'recommendations') getRecommendations();
            if (name === 'readlist') loadReadlist();
        }

        function updateStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    totalPapers = data.total_papers;
                    // Merge server ratings into local state rather than
                    // replacing wholesale.  If the user clicked a rating
                    // between when the fetch was sent and when it resolved,
                    // a wholesale replacement would silently discard that
                    // click and cause the next renderPaper() call (e.g. on
                    // tab switch) to show stale state.
                    Object.assign(ratings, data.ratings);
                    Object.entries(data.readlist).forEach(([k, p]) => readlist.set(k, p));
                    updateStatsLocal();
                });
        }

        function renderPaper(paper, score = null, showPriority = false) {
            const key = paper.dblp_key;
            const escapedKey = escapeHtml(key);
            const currentRating = ratings[key] || 0;
            const safeKey = key.replace(/[^a-zA-Z0-9]/g, '_');
            const ratingButtons = [-1, 1, 2, 3, 4, 5].map(r => {
                const selected = currentRating === r ? 'selected' : '';
                const irrelevant = r === -1 ? 'irrelevant' : '';
                const label = r === -1 ? 'Irrelevant' : r;
                return `<button data-rating="${r}" class="${selected} ${irrelevant}" onclick="rate('${escapedKey}', ${r})">${label}</button>`;
            }).join('');

            const scoreHtml = score !== null ? `<span class="rec-score">${score.toFixed(3)}</span>` : '';
            const doiLink = paper.doi ? `<a href="https://doi.org/${escapeHtml(paper.doi)}" target="_blank">DOI</a>` : '';
            const authors = (paper.authors || []).slice(0, 3).map(a => escapeHtml(a)).join(', ') + (paper.authors && paper.authors.length > 3 ? ' et al.' : '');
            const ratedIrrelevant = currentRating === -1 ? 'rated-irrelevant' : '';

            const inReadlist = readlist.has(key);
            const readlistBtnClass = inReadlist ? 'readlist-btn in-readlist' : 'readlist-btn';
            const readlistBtnText = inReadlist ? '✓ In Read List' : '+ Read Later';
            const clearBtn = currentRating ? `<button class="clear-btn" onclick="clearRating('${escapedKey}')" title="Clear rating">×</button>` : '';

            const abstractHtml = paper.abstract
                ? `<div class="paper-abstract"><strong>Abstract:</strong> ${escapeHtml(paper.abstract)}</div>`
                : '';

            let rankHtml = '';
            if (showPriority && readlist.has(key)) {
                rankHtml = `<span class="rank-control" data-rank-key="${escapedKey}"><span class="rank-label">#${readlist.get(key)}</span><button onclick="moveReadlist('${escapedKey}', 'up')" title="Move up">+</button><button onclick="moveReadlist('${escapedKey}', 'down')" title="Move down">&minus;</button></span>`;
            }

            return `
                <div class="paper ${ratedIrrelevant}" id="paper-${safeKey}" data-key="${escapedKey}">
                    <div class="paper-title">${scoreHtml}${escapeHtml(paper.title) || 'Untitled'}</div>
                    <div class="paper-authors">${authors}</div>
                    <div class="paper-meta">
                        ${escapeHtml(paper.year)} | ${escapeHtml(paper.venue) || 'TOG'} | ${doiLink}
                        <br><small style="color:#999">${escapedKey}</small>
                    </div>
                    ${abstractHtml}
                    <div class="rating-buttons" data-key="${escapedKey}">
                        Rate: ${ratingButtons}
                        <span class="score">${currentRating ? `Current: ${currentRating}` : ''}</span>
                        ${clearBtn}
                        <button class="${readlistBtnClass}" onclick="toggleReadlist('${escapedKey}')">${readlistBtnText}</button>
                        ${rankHtml}
                    </div>
                </div>
            `;
        }

        function search() {
            const query = document.getElementById('searchQuery').value;
            if (!query) return;

            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(r => r.json())
                .then(data => {
                    cachedSearchPapers = data.papers;
                    document.getElementById('searchSortControl').style.display = cachedSearchPapers.length > 0 ? 'flex' : 'none';
                    document.getElementById('searchSort').value = 'relevance';
                    renderSearchResults();
                });
        }

        function renderSearchResults() {
            const sort = document.getElementById('searchSort').value;
            const papers = [...cachedSearchPapers];
            if (sort === 'year') {
                papers.sort((a, b) => (b.year || 0) - (a.year || 0));
            } else if (sort === 'year-asc') {
                papers.sort((a, b) => (a.year || 0) - (b.year || 0));
            }
            // 'relevance' keeps original API order

            if (papers.length === 0) {
                document.getElementById('searchResults').innerHTML = '<div class="no-results">No papers found</div>';
            } else {
                document.getElementById('searchResults').innerHTML = papers.map(p => renderPaper(p)).join('');
            }
        }

        function updatePaperCard(key) {
            // Surgically update every on-screen card for this paper.
            // Avoids replacing the whole card (which would destroy &
            // recreate DOM nodes, losing hover state and causing a
            // visible flicker that masks the actual change).
            const currentRating = ratings[key] || 0;
            const inReadlist = readlist.has(key);

            document.querySelectorAll('[data-key="' + escapeHtml(key) + '"]').forEach(paperEl => {
                // --- rating buttons ---
                paperEl.querySelectorAll('button[data-rating]').forEach(btn => {
                    btn.classList.toggle('selected', parseInt(btn.dataset.rating) === currentRating);
                });

                // --- "Current: N" label ---
                const scoreSpan = paperEl.querySelector('.rating-buttons .score');
                if (scoreSpan) {
                    scoreSpan.textContent = currentRating ? 'Current: ' + currentRating : '';
                }

                // --- clear button: add if rated, remove if not ---
                let clearBtn = paperEl.querySelector('.clear-btn');
                if (currentRating && !clearBtn) {
                    clearBtn = document.createElement('button');
                    clearBtn.className = 'clear-btn';
                    clearBtn.textContent = '\u00d7';
                    clearBtn.title = 'Clear rating';
                    clearBtn.setAttribute('onclick', "clearRating('" + escapeHtml(key) + "')");
                    scoreSpan.insertAdjacentElement('afterend', clearBtn);
                } else if (!currentRating && clearBtn) {
                    clearBtn.remove();
                }

                // --- readlist button ---
                const rlBtn = paperEl.querySelector('.readlist-btn');
                if (rlBtn) {
                    rlBtn.classList.toggle('in-readlist', inReadlist);
                    rlBtn.textContent = inReadlist ? '\u2713 In Read List' : '+ Read Later';
                }

                // --- rank controls: remove when paper leaves readlist ---
                const rankCtrl = paperEl.querySelector('.rank-control');
                if (!inReadlist && rankCtrl) {
                    rankCtrl.remove();
                }

                // --- card-level classes ---
                paperEl.classList.toggle('rated-irrelevant', currentRating === -1);
            });
        }

        function rate(key, score) {
            ratings[key] = score;
            updatePaperCard(key);
            updateStatsLocal();

            // Send to server (fire and forget)
            fetch('/api/rate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key: key, score: score})
            });
        }

        function clearRating(key) {
            delete ratings[key];
            updatePaperCard(key);
            updateStatsLocal();

            // Send to server (score=0 removes the rating)
            fetch('/api/rate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key: key, score: 0})
            });
        }

        function updateStatsLocal() {
            // Quick local stats update without server round-trip
            const statsEl = document.getElementById('stats');
            const positive = Object.values(ratings).filter(v => v > 0).length;
            const negative = Object.values(ratings).filter(v => v < 0).length;
            const total = Object.keys(ratings).length;
            statsEl.innerHTML = `<strong>${totalPapers}</strong> papers |
                <strong>${total}</strong> rated
                (${positive} liked, ${negative} irrelevant) |
                <strong>${readlist.size}</strong> in read list`;
        }

        function getRecommendations() {
            document.getElementById('recResults').innerHTML = '<div class="no-results">Loading recommendations...</div>';
            fetch('/api/recommendations?n=30')
                .then(r => r.json())
                .then(data => {
                    if (data.recommendations.length === 0) {
                        document.getElementById('recResults').innerHTML = '<div class="no-results">Rate some papers first to get recommendations!</div>';
                    } else {
                        document.getElementById('recResults').innerHTML = data.recommendations.map(r => renderPaper(r.paper, r.score)).join('');
                    }
                });
        }

        function loadRated() {
            const sort = document.getElementById('ratedSort').value;
            fetch(`/api/rated?sort=${sort}`)
                .then(r => r.json())
                .then(data => {
                    if (data.papers.length === 0) {
                        document.getElementById('ratedPapers').innerHTML = '<div class="no-results">No papers rated yet</div>';
                    } else {
                        document.getElementById('ratedPapers').innerHTML = data.papers.map(p => renderPaper(p)).join('');
                    }
                });
        }

        function loadReadlist() {
            const sort = document.getElementById('readlistSort').value;
            fetch(`/api/readlist?sort=${sort}`)
                .then(r => r.json())
                .then(data => {
                    // Update local rank map with raw rank values
                    data.papers.forEach(p => readlist.set(p.paper.dblp_key, p.rank));
                    if (data.papers.length === 0) {
                        document.getElementById('readlistPapers').innerHTML = '<div class="no-results">No papers in read list yet. Click "+ Read Later" on any paper to add it.</div>';
                    } else {
                        document.getElementById('readlistPapers').innerHTML = data.papers.map((p, i) => renderPaper(p.paper, p.score, true)).join('');
                    }
                });
        }

        function toggleReadlist(key) {
            const inList = readlist.has(key);
            const action = inList ? 'remove' : 'add';

            // Optimistic local update
            if (inList) {
                readlist.delete(key);
            } else {
                readlist.set(key, readlist.size + 1);
            }

            // Update all cards for this paper in place
            updatePaperCard(key);

            // Update stats
            updateStatsLocal();

            // Send to server
            fetch('/api/readlist/' + action, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key: key})
            });
        }

        function moveReadlist(key, direction) {
            // Change raw rank by 1
            const newRank = readlist.get(key) + (direction === 'up' ? -1 : 1);
            readlist.set(key, newRank);

            // Update only this card's rank label
            document.querySelectorAll('[data-rank-key="' + escapeHtml(key) + '"] .rank-label')
                .forEach(el => el.textContent = '#' + newRank);

            // Send to server (fire and forget)
            fetch('/api/readlist/move', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key: key, direction: direction})
            });
        }

        // Theme toggle
        function toggleTheme() {
            document.body.classList.toggle('dark');
            const isDark = document.body.classList.contains('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            updateThemeButton();
        }

        function updateThemeButton() {
            const btn = document.querySelector('.theme-toggle');
            const isDark = document.body.classList.contains('dark');
            btn.textContent = isDark ? '☀️ Light Mode' : '🌙 Dark Mode';
        }

        function loadTheme() {
            const saved = localStorage.getItem('theme');
            if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                document.body.classList.add('dark');
            }
            updateThemeButton();
        }

        // Initial load
        loadTheme();
        updateStats();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def stats():
    positive = sum(1 for v in rec.ratings.values() if v > 0)
    negative = sum(1 for v in rec.ratings.values() if v < 0)
    return jsonify({
        'total_papers': len(rec.papers),
        'total_ratings': len(rec.ratings),
        'positive_ratings': positive,
        'negative_ratings': negative,
        'ratings': rec.ratings,
        'readlist': rec.readlist,
        'readlist_count': len(rec.readlist)
    })

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    papers = rec.find_paper(query) if query else []
    return jsonify({'papers': papers})

@app.route('/api/rate', methods=['POST'])
def rate():
    data = request.json
    key = data.get('key')
    score = data.get('score')
    if key and score is not None:
        if score == 0:
            # Remove rating
            rec.ratings.pop(key, None)
            rec.save_ratings()
        else:
            rec.rate_paper(key, score)
    return jsonify({'success': True})

@app.route('/api/recommendations')
def recommendations():
    n = int(request.args.get('n', 20))
    recs = rec.get_recommendations(top_k=n)
    return jsonify({
        'recommendations': [{'paper': p, 'score': s} for p, s in recs]
    })

@app.route('/api/rated')
def rated():
    sort = request.args.get('sort', 'rating')
    papers = []
    for key in rec.ratings:
        paper = rec.get_paper_by_key(key)
        if paper:
            papers.append(paper)

    # Sort based on parameter
    if sort == 'year':
        papers.sort(key=lambda p: p.get('year', 0), reverse=True)
    elif sort == 'year-asc':
        papers.sort(key=lambda p: p.get('year', 0))
    else:  # rating (default)
        papers.sort(key=lambda p: rec.ratings.get(p['dblp_key'], 0), reverse=True)

    return jsonify({'papers': papers})

@app.route('/api/readlist')
def get_readlist():
    sort = request.args.get('sort', 'relevance')
    papers = []
    keys = list(rec.readlist)

    # Get relevance scores
    scores = rec.get_relevance_scores(keys)

    for key in keys:
        paper = rec.get_paper_by_key(key)
        if paper:
            papers.append({
                'paper': paper,
                'score': scores.get(key, 0),
                'rank': rec.readlist.get(key, 0)
            })

    # Sort based on parameter
    if sort == 'year':
        papers.sort(key=lambda p: p['paper'].get('year', 0), reverse=True)
    elif sort == 'year-asc':
        papers.sort(key=lambda p: p['paper'].get('year', 0))
    elif sort == 'relevance':
        papers.sort(key=lambda p: p['score'], reverse=True)
    else:  # rank (default)
        papers.sort(key=lambda p: p['rank'])

    return jsonify({'papers': papers})

@app.route('/api/readlist/add', methods=['POST'])
def add_to_readlist():
    data = request.json
    key = data.get('key')
    if key:
        rec.add_to_readlist(key)
    return jsonify({'success': True})

@app.route('/api/readlist/move', methods=['POST'])
def move_in_readlist():
    data = request.json
    key = data.get('key')
    direction = data.get('direction')
    if key and direction == 'up':
        rec.move_readlist_up(key)
    elif key and direction == 'down':
        rec.move_readlist_down(key)
    return jsonify({'success': True})

@app.route('/api/readlist/remove', methods=['POST'])
def remove_from_readlist():
    data = request.json
    key = data.get('key')
    if key:
        rec.remove_from_readlist(key)
    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Paper Recommender Web Interface")
    print("="*50)
    print("\nOpen your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    app.run(debug=False, port=5000)
