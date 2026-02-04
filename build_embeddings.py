#!/usr/bin/env python
"""
Build embeddings for the paper database.

This script computes SPECTER2 embeddings for all papers using their
titles and abstracts (when available).

Input: data/all_papers_enriched.json
Output: data/embeddings_with_abstracts.npy
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).parent / "data"
PAPERS_FILE = DATA_DIR / "all_papers_enriched.json"
EMBEDDINGS_FILE = DATA_DIR / "embeddings_with_abstracts.npy"

MODEL_NAME = "allenai/specter2_base"


def paper_text(paper: dict) -> str:
    """Get text representation of a paper for embedding."""
    title = paper.get("title") or ""
    abstract = paper.get("abstract") or ""
    if abstract:
        return f"{title} {abstract}"
    return title


def main():
    print("=" * 60)
    print("Building Paper Embeddings")
    print("=" * 60)

    # Load papers
    print(f"\nLoading papers from {PAPERS_FILE}...")
    with open(PAPERS_FILE, "r", encoding="utf-8") as f:
        papers = json.load(f)
    print(f"Loaded {len(papers)} papers")

    # Stats
    with_abstract = sum(1 for p in papers if p.get("abstract"))
    print(f"Papers with abstracts: {with_abstract} ({100 * with_abstract / len(papers):.1f}%)")

    # Load model
    print(f"\nLoading model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    # Prepare texts
    texts = [paper_text(p) for p in papers]

    # Compute embeddings
    print(f"\nComputing embeddings for {len(texts)} papers...")
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    # Save
    np.save(EMBEDDINGS_FILE, embeddings)

    print("\n" + "=" * 60)
    print("Embeddings Build Complete")
    print("=" * 60)
    print(f"Embedding shape: {embeddings.shape}")
    print(f"Output: {EMBEDDINGS_FILE}")


if __name__ == "__main__":
    main()
