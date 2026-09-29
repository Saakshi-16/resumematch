"""
STEP 4 of RAG: the search index -- a TWO-STAGE retrieval pipeline.

STAGE 1 - HYBRID CANDIDATE SEARCH (fast)
  - Semantic search : cosine similarity between embeddings (same MEANING)
  - Keyword search  : BM25 (same WORDS -- important for exact skills like "FAISS", "SQL")
  - Several queries can be searched at once (e.g. the requirement + a HyDE hypothetical line)
  - All ranked lists are merged with Reciprocal Rank Fusion (RRF):  score = sum 1 / (60 + rank)

STAGE 2 - CROSS-ENCODER RERANKING (precise)
  - The top candidates are re-scored by a cross-encoder that reads query + chunk together.
"""
import math
from collections import Counter
import re

import numpy as np

from . import embedder, reranker
from .chunker import search_text

STOPWORDS = set(
    "a an the and or of to in on for with at by from is are was were be been this that it as i my me we our you your "
    "do does did have has had will would can could should what which who how when where why any all into about".split()
)
RRF_K = 60


def tokenize(text):
    words = re.findall(r"[a-z0-9][a-z0-9+#.\-]*", text.lower())
    return [w.strip(".-") for w in words if w not in STOPWORDS and w.strip(".-")]


class BM25:
    """Keyword relevance score (the formula used by Elasticsearch / Lucene).
    Rewards chunks containing the query words, especially RARE words, without over-rewarding repetition."""

    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.tfs = [Counter(d) for d in docs]
        self.lens = [len(d) for d in docs]
        self.avg = (sum(self.lens) / len(docs)) if docs else 0
        n = len(docs)
        df = Counter(w for d in docs for w in set(d))
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}  # always positive

    def get_scores(self, query):
        scores = []
        for tf, length in zip(self.tfs, self.lens):
            s = 0.0
            for w in query:
                if w in tf:
                    f = tf[w]
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / (self.avg or 1)))
            scores.append(s)
        return scores


class HybridIndex:
    def __init__(self, chunks, vectors=None):
        self.chunks = chunks
        self.vectors = vectors  # numpy array (n_chunks x 384) or None
        self.bm25 = BM25([tokenize(search_text(c)) for c in chunks]) if chunks else None

    @classmethod
    def build(cls, chunks):
        return cls(chunks, embedder.embed_passages([search_text(c) for c in chunks]))

    @property
    def mode(self):
        return "hybrid" if self.vectors is not None else "keyword"

    # ---------- stage 1 building blocks ----------
    def _candidates(self, source):
        return [i for i, c in enumerate(self.chunks) if source is None or c["source"] == source]

    def keyword_rank(self, query, ids):
        scores = self.bm25.get_scores(tokenize(query))
        ranked = [i for i in sorted(ids, key=lambda i: scores[i], reverse=True) if scores[i] > 0]
        return ranked, {i: float(scores[i]) for i in ids}

    def semantic_rank(self, query, ids):
        if self.vectors is None:
            return [], {}
        q = embedder.embed_query(query)
        if q is None:
            return [], {}
        sims = self.vectors @ q
        return sorted(ids, key=lambda i: sims[i], reverse=True), {i: float(sims[i]) for i in ids}

    # ---------- the full pipeline ----------
    def search(self, query, k=5, source=None, mode="hybrid", rerank=False, extra_queries=None, n_candidates=15):
        """
        mode          : "keyword" | "semantic" | "hybrid"  (stage 1)
        rerank        : True -> stage 2 cross-encoder reranking
        extra_queries : more query texts to search with (e.g. HyDE hypothetical resume lines)
        """
        ids = self._candidates(source)
        if not ids:
            return []
        queries = [query] + [q for q in (extra_queries or []) if q]

        fused, sem_best, kw_best = {}, {}, {}
        for q in queries:
            lists = []
            if mode in ("hybrid", "keyword"):
                ranked, scores = self.keyword_rank(q, ids)
                lists.append(ranked)
                for i, s in scores.items():
                    kw_best[i] = max(kw_best.get(i, 0.0), s)
            if mode in ("hybrid", "semantic"):
                ranked, scores = self.semantic_rank(q, ids)
                lists.append(ranked)
                for i, s in scores.items():
                    sem_best[i] = max(sem_best.get(i, -1.0), s)
            for ranked in lists:
                for rank, i in enumerate(ranked[:30]):
                    fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)  # Reciprocal Rank Fusion

        order = sorted(fused, key=fused.get, reverse=True)
        rerank_scores = {}
        if rerank and order:
            candidates = order[:n_candidates]
            scores = reranker.score(query, [search_text(self.chunks[i]) for i in candidates])
            if scores is not None:
                rerank_scores = dict(zip(candidates, scores))
                order = sorted(candidates, key=lambda i: rerank_scores[i], reverse=True)

        results = []
        for i in order[:k]:
            c = dict(self.chunks[i])
            c["score"] = round(fused[i], 4)
            c["semantic"] = round(sem_best[i], 3) if i in sem_best else None
            c["keyword"] = round(kw_best[i], 3) if i in kw_best else None
            c["rerank"] = round(rerank_scores[i], 3) if i in rerank_scores else None
            results.append(c)
        return results
