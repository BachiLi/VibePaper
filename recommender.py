"""
Paper Recommender System using embedding-based similarity.
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).parent / "data"
PAPERS_FILE = DATA_DIR / "papers.json"
EMBEDDINGS_FILE = DATA_DIR / "embeddings_with_abstracts.npy"
RATINGS_FILE = DATA_DIR / "ratings.json"
READLIST_FILE = DATA_DIR / "readlist.json"

# SPECTER2 is designed for scientific papers
# Falls back to a general model if SPECTER2 is unavailable
MODEL_NAME = "allenai/specter2_base"


class PaperRecommender:
    def __init__(self):
        self.papers: list[dict] = []
        self.embeddings: np.ndarray | None = None
        self.ratings: dict[str, float] = {}  # dblp_key -> score (-1 for irrelevant, 1-5 for rated)
        self.readlist: set[str] = set()  # dblp_keys of papers to read
        self.model: SentenceTransformer | None = None

    def load_papers(self, path: Path = PAPERS_FILE):
        """Load papers from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            self.papers = json.load(f)
        print(f"Loaded {len(self.papers)} papers")

    def load_embeddings(self, path: Path = EMBEDDINGS_FILE):
        """Load pre-computed embeddings."""
        if path.exists():
            self.embeddings = np.load(path)
            print(f"Loaded embeddings: {self.embeddings.shape}")
        else:
            print("No embeddings found. Run compute_embeddings() first.")

    def load_ratings(self, path: Path = RATINGS_FILE):
        """Load user ratings."""
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self.ratings = json.load(f)
            print(f"Loaded {len(self.ratings)} ratings")

    def save_ratings(self, path: Path = RATINGS_FILE):
        """Save user ratings."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.ratings, f, indent=2)

    def load_readlist(self, path: Path = READLIST_FILE):
        """Load reading list."""
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self.readlist = set(json.load(f))
            print(f"Loaded {len(self.readlist)} papers in readlist")

    def save_readlist(self, path: Path = READLIST_FILE):
        """Save reading list."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(self.readlist), f, indent=2)

    def add_to_readlist(self, dblp_key: str):
        """Add a paper to reading list."""
        self.readlist.add(dblp_key)
        self.save_readlist()

    def remove_from_readlist(self, dblp_key: str):
        """Remove a paper from reading list."""
        self.readlist.discard(dblp_key)
        self.save_readlist()

    def _get_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self.model is None:
            print(f"Loading model {MODEL_NAME}...")
            self.model = SentenceTransformer(MODEL_NAME)
        return self.model

    def _paper_text(self, paper: dict) -> str:
        """Get text representation of a paper for embedding."""
        title = paper.get("title") or ""
        abstract = paper.get("abstract") or ""
        if abstract:
            return f"{title} {abstract}"
        return title

    def compute_embeddings(self, batch_size: int = 32):
        """Compute embeddings for all papers."""
        model = self._get_model()
        texts = [self._paper_text(p) for p in self.papers]

        print(f"Computing embeddings for {len(texts)} papers...")
        self.embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
        )

        np.save(EMBEDDINGS_FILE, self.embeddings)
        print(f"Saved embeddings to {EMBEDDINGS_FILE}")

    def rate_paper(self, dblp_key: str, score: float):
        """
        Rate a paper.
        score: -1 for irrelevant, 1-5 for interest level
        """
        self.ratings[dblp_key] = score
        self.save_ratings()

    # Number of nearest rated papers to average for scoring
    TOPK_NEIGHBORS = 5

    def _compute_similarities(self):
        """
        Compute per-paper similarity scores using top-k average similarity.
        For each candidate paper, find its top-k most similar positively rated
        papers and average those similarities (weighted by rating).
        Returns (similarities array, key_to_idx dict) or (None, None).
        """
        if not self.ratings or self.embeddings is None:
            return None, None

        key_to_idx = {p["dblp_key"]: i for i, p in enumerate(self.papers)}

        positive_indices = []
        positive_weights = []
        negative_indices = []

        for key, score in self.ratings.items():
            if key not in key_to_idx:
                continue
            idx = key_to_idx[key]
            if score > 0:
                positive_indices.append(idx)
                positive_weights.append(score)
            else:
                negative_indices.append(idx)

        if not positive_indices:
            return None, None

        # Normalize all embeddings
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)  # avoid division by zero
        embeddings_norm = self.embeddings / norms

        # Compute similarity of every paper to every positively rated paper
        pos_embeddings = embeddings_norm[positive_indices]  # (n_pos, dim)
        pos_weights = np.array(positive_weights)  # (n_pos,)
        sim_matrix = embeddings_norm @ pos_embeddings.T  # (n_papers, n_pos)

        # For each paper, take weighted average of top-k most similar rated papers
        k = min(self.TOPK_NEIGHBORS, len(positive_indices))
        if k == len(positive_indices):
            # Use all rated papers, weighted average
            weighted = sim_matrix * pos_weights[np.newaxis, :]
            similarities = weighted.sum(axis=1) / pos_weights.sum()
        else:
            # For each paper, find the top-k most similar rated papers
            top_k_indices = np.argpartition(sim_matrix, -k, axis=1)[:, -k:]
            similarities = np.zeros(len(self.papers))
            for i in range(len(self.papers)):
                top_idx = top_k_indices[i]
                top_sims = sim_matrix[i, top_idx]
                top_w = pos_weights[top_idx]
                similarities[i] = np.average(top_sims, weights=top_w)

        # Penalize papers similar to negatively rated ones using top-k negatives
        if negative_indices:
            neg_embeddings = embeddings_norm[negative_indices]
            neg_sims = embeddings_norm @ neg_embeddings.T  # (n_papers, n_neg)
            k_neg = min(self.TOPK_NEIGHBORS, len(negative_indices))
            if k_neg == len(negative_indices):
                neg_penalty = neg_sims.mean(axis=1)
            else:
                top_neg_indices = np.argpartition(neg_sims, -k_neg, axis=1)[:, -k_neg:]
                neg_penalty = np.array([
                    neg_sims[i, top_neg_indices[i]].mean()
                    for i in range(len(self.papers))
                ])
            similarities = similarities - 0.5 * neg_penalty

        return similarities, key_to_idx

    def get_recommendations(self, top_k: int = 20) -> list[tuple[dict, float]]:
        """
        Get paper recommendations based on ratings.
        Returns list of (paper, score) tuples.
        """
        similarities, key_to_idx = self._compute_similarities()
        if similarities is None:
            return []

        # Rank and filter out already-rated papers and papers in readlist
        rated_indices = {key_to_idx[k] for k in self.ratings if k in key_to_idx}
        readlist_indices = {key_to_idx[k] for k in self.readlist if k in key_to_idx}
        exclude_indices = rated_indices | readlist_indices
        ranked_indices = np.argsort(similarities)[::-1]

        results = []
        for idx in ranked_indices:
            if idx in exclude_indices:
                continue
            results.append((self.papers[idx], float(similarities[idx])))
            if len(results) >= top_k:
                break

        return results

    def get_relevance_scores(self, keys: list[str]) -> dict[str, float]:
        """
        Compute relevance scores for specific papers.
        Returns dict mapping dblp_key -> relevance score.
        """
        similarities, key_to_idx = self._compute_similarities()
        if similarities is None:
            return {}

        scores = {}
        for key in keys:
            if key in key_to_idx:
                idx = key_to_idx[key]
                scores[key] = float(similarities[idx])

        return scores

    def find_paper(self, query: str) -> list[dict]:
        """Search for papers by title or author."""
        query_lower = query.lower()
        matches = []
        for p in self.papers:
            title = p.get("title") or ""
            authors = p.get("authors") or []
            authors_str = " ".join(authors).lower()
            if query_lower in title.lower() or query_lower in authors_str:
                matches.append(p)
        return matches[:50]

    def get_paper_by_key(self, key: str) -> dict | None:
        """Get a paper by its DBLP key."""
        for p in self.papers:
            if p["dblp_key"] == key:
                return p
        return None


def main():
    """Interactive CLI for the recommender."""
    rec = PaperRecommender()
    rec.load_papers()
    rec.load_embeddings()
    rec.load_ratings()

    print("\nCommands:")
    print("  search <query>  - Search papers by title")
    print("  rate <key> <score> - Rate a paper (-1=irrelevant, 1-5=interest)")
    print("  rec [n]         - Get n recommendations (default 10)")
    print("  embed           - Compute embeddings (takes a while)")
    print("  quit            - Exit")

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()

        if action == "quit":
            break

        elif action == "search" and len(parts) > 1:
            matches = rec.find_paper(parts[1])
            for p in matches:
                score = rec.ratings.get(p["dblp_key"], "")
                score_str = f" [rated: {score}]" if score else ""
                print(f"  {p['dblp_key']}: {p['title']} ({p['year']}){score_str}")

        elif action == "rate":
            args = parts[1].split() if len(parts) > 1 else []
            if len(args) >= 2:
                key, score = args[0], float(args[1])
                paper = rec.get_paper_by_key(key)
                if paper:
                    rec.rate_paper(key, score)
                    print(f"Rated '{paper['title']}' as {score}")
                else:
                    print(f"Paper not found: {key}")
            else:
                print("Usage: rate <dblp_key> <score>")

        elif action == "rec":
            n = int(parts[1]) if len(parts) > 1 else 10
            recs = rec.get_recommendations(top_k=n)
            for i, (p, score) in enumerate(recs, 1):
                print(f"{i:2}. [{score:.3f}] {p['title']} ({p['year']})")
                print(f"      Key: {p['dblp_key']}")

        elif action == "embed":
            rec.compute_embeddings()

        else:
            print("Unknown command. Type 'quit' to exit.")


if __name__ == "__main__":
    main()
