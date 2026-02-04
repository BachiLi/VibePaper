# Academic Paper Recommender - Approaches

## Overview
Zero-shot paper recommendation system where user provides scores (or marks "irrelevant") and system recommends similar papers.

---

## 1. Embedding-Based Similarity

Use pre-trained models to embed papers, find similar ones to highly-rated papers.

**Models:**
- **SPECTER/SPECTER2** - Trained on scientific papers (recommended)
- **SciBERT** - BERT fine-tuned on scientific text
- **Sentence-BERT** - General purpose, fast
- **OpenAI/Voyage embeddings** - Commercial, high quality

**Method:**
- Embed all candidate papers (title + abstract)
- Embed liked papers
- Rank by cosine similarity (weighted by scores)
- Subtract similarity to "irrelevant" papers

---

## 2. LLM-Based Preference Learning

Use LLM to understand *why* user likes certain papers, then score new ones.

**Approaches:**
- Few-shot prompting with rated papers as examples
- Extract preference criteria from ratings
- Score new papers against learned criteria

**Pros:** Captures nuanced preferences (methodology, writing style, novelty)
**Cons:** API costs, slower, less reproducible

---

## 3. Citation/Graph-Based

Using citation data (e.g., Semantic Scholar API):
- Recommend papers cited by liked papers
- Recommend papers that cite liked papers
- Graph embeddings (node2vec, GNN) on citation network

---

## 4. Keyword/Topic-Based

- Extract keywords (RAKE, KeyBERT)
- TF-IDF similarity
- Topic modeling (LDA, BERTopic)

**Pros:** Interpretable
**Cons:** Misses semantic similarity

---

## 5. Learning to Rank

Train lightweight model on ratings:
- Features: embeddings + metadata (year, venue, citation count, author h-index)
- Models: logistic regression, small neural net, XGBoost
- Works with ~50-100 rated papers

---

## 6. Active Learning Loop

Intelligently select which papers to rate:
- Uncertainty sampling
- Diversity sampling
- Maximizes information per rating

---

## Recommended Hybrid Approach

1. **SPECTER2 embeddings** as foundation
2. **Weighted similarity** (subtract "irrelevant" embeddings)
3. **Optional LLM layer** for re-ranking/explanations
4. **Active learning** for efficient improvement

---

## Data Sources

- **DBLP** - Bibliographic data, metadata
- **Semantic Scholar** - Abstracts, citations, embeddings
- **arXiv** - Full text for CS/Math/Physics papers
- **OpenAlex** - Open bibliographic data
