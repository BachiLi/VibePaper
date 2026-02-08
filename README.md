# VibePaper

A recommendation system for SIGGRAPH/TOG papers using SPECTER2 embeddings.
As the name suggests, this project is 100% vibe-coded by Claude Code.

Rate papers you like (or mark as irrelevant), and get personalized recommendations for similar papers.

<img width="1214" height="849" alt="Screenshot 2026-02-03 215823" src="https://github.com/user-attachments/assets/a8abb3de-bedb-4d26-9bf4-961c7fcac50d" />

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/BachiLi/VibePaper.git
cd VibePaper

# Install dependencies
uv sync

# Build embeddings (required on first run, ~7 minutes)
uv run python build.py embeddings
```

### Running

```bash
uv run python app.py
```

Open http://localhost:5000 in your browser.

## Usage

1. **Search** for papers by title in the Search tab
2. **Rate** papers from 1-5 stars (or mark as irrelevant with -1)
3. **Get recommendations** in the Recommendations tab based on your ratings
4. **Save papers** to your Read Later list for tracking

The more papers you rate, the better the recommendations become.

## Rebuilding the Database

To fetch the latest papers from DBLP and refresh abstracts:

```bash
# Rebuild everything (database + embeddings)
uv run python build.py

# Or rebuild separately:
uv run python build.py database   # Fetch papers and abstracts (~20 minutes)
uv run python build.py embeddings # Compute embeddings (~7 minutes)
```

## How It Works

1. **Paper embeddings**: Each paper is embedded using [SPECTER2](https://huggingface.co/allenai/specter2_base), a model trained specifically for scientific papers. The embedding uses the paper's title and abstract.

2. **User preference modeling**: Your positive ratings (1-5) are used to compute a weighted average embedding representing your interests. Higher ratings have more influence.

3. **Recommendations**: Papers are ranked by cosine similarity to your preference embedding. Papers marked as irrelevant (-1) reduce the score of similar papers.

4. **Data sources**:
   - Paper metadata: [DBLP](https://dblp.org/)
   - Abstracts: [Crossref](https://www.crossref.org/), [Semantic Scholar](https://www.semanticscholar.org/), [OpenAlex](https://openalex.org/), and [SIGGRAPH History Archive](https://history.siggraph.org/)

## File Structure

```
VibePaper/
├── app.py                      # Flask web interface
├── recommender.py              # Recommendation engine
├── build.py                    # Main build script
├── build_database.py           # Fetches papers and abstracts
├── build_embeddings.py         # Computes SPECTER2 embeddings
├── fetch_crossref_abstracts.py # Fetch abstracts from Crossref API
├── fetch_s2_abstracts.py       # Fetch abstracts from Semantic Scholar (Playwright)
├── edit_abstracts.py           # Local web UI for manually editing missing abstracts
├── paper_io.py                 # Shared file I/O with locking
├── data/
│   ├── all_papers_enriched.json       # Paper database (7120 papers, 100% with abstracts)
│   ├── embeddings_with_abstracts.npy  # Paper embeddings (generated)
│   ├── ratings.json                   # Your ratings (generated)
│   └── readlist.json                  # Your reading list (generated)
└── pyproject.toml              # Dependencies
```

## License

MIT
