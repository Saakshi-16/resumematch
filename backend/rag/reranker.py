"""
STAGE 2 of retrieval: a CROSS-ENCODER RERANKER.

Stage 1 (hybrid search) is fast but approximate: the query and each chunk are turned into
vectors SEPARATELY. A cross-encoder reads the query and a chunk TOGETHER in one neural
network pass, so it understands how well they match much more precisely -- but it is slower,
so we only run it on the ~15 best candidates from stage 1.

Model: Xenova/ms-marco-MiniLM-L-6-v2 (80 MB, trained on Microsoft's MS MARCO search dataset).
If it cannot load, the app simply skips reranking.
"""
import math
import threading

from django.conf import settings

MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
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
                from fastembed.rerank.cross_encoder import TextCrossEncoder
                settings.MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                _model = TextCrossEncoder(MODEL, cache_dir=str(settings.MODEL_CACHE_DIR))
            except Exception as e:  # noqa: BLE001
                _error = str(e)
                print(f"[reranker] Cross-encoder unavailable, skipping reranking: {e}")
    return _model


def available():
    return _load() is not None


def score(query, texts):
    """Returns a relevance probability (0-1) for each text, or None if the model is unavailable."""
    model = _load()
    if model is None or not texts:
        return None
    logits = list(model.rerank(query, texts))
    return [1 / (1 + math.exp(-float(x))) for x in logits]  # sigmoid: logit -> 0..1
