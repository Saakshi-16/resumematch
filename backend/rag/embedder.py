"""
STEP 3 of RAG: turn text into "embeddings" (lists of numbers that capture meaning).
Similar meaning -> similar numbers, so "ML" and "machine learning" end up close together.

We use a small free model (BAAI/bge-small-en-v1.5) that runs on the CPU via fastembed.
If it cannot load (e.g. no internet on first run), the app still works using keyword search only.
"""
import threading

import numpy as np
from django.conf import settings

_model = None
_error = None
_lock = threading.Lock()


def _load():
    global _model, _error
    if _model is not None or _error is not None:
        return _model
    with _lock:
        if _model is None and _error is None:
            try:
                from fastembed import TextEmbedding
                settings.MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                _model = TextEmbedding(settings.EMBEDDING_MODEL, cache_dir=str(settings.MODEL_CACHE_DIR))
            except Exception as e:  # noqa: BLE001
                _error = str(e)
                print(f"[embedder] Semantic model unavailable, using keyword search only: {e}")
    return _model


def available():
    return _load() is not None


def status():
    from . import reranker
    _load()
    stage1 = "semantic + keyword (hybrid)" if _model is not None else "keyword only (embedding model not loaded)"
    stage2 = " + cross-encoder reranking" if reranker.available() else ""
    return stage1 + stage2


def _normalize(vectors):
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)


def embed_passages(texts):
    model = _load()
    if model is None or not texts:
        return None
    return _normalize(list(model.passage_embed(texts)))


def embed_query(text):
    model = _load()
    if model is None:
        return None
    return _normalize(list(model.query_embed([text])))[0]
