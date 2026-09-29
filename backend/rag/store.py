"""
Saves / loads each analysis in its own folder: storage/<analysis_id>/
  meta.json    -> file names, full texts, the report
  chunks.json  -> the text chunks
  vectors.npy  -> the embeddings (numbers) for each chunk
"""
import json
import re
import uuid

import numpy as np
from django.conf import settings

from .index import HybridIndex

_cache = {}  # keeps recently used indexes in memory so chat is fast


def _dir(analysis_id):
    if not re.fullmatch(r"[a-f0-9]{32}", analysis_id or ""):
        raise KeyError("Invalid analysis id")
    return settings.STORAGE_DIR / analysis_id


def new_id():
    return uuid.uuid4().hex


def save(analysis_id, meta, index):
    d = _dir(analysis_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (d / "chunks.json").write_text(json.dumps(index.chunks), encoding="utf-8")
    if index.vectors is not None:
        np.save(d / "vectors.npy", index.vectors)
    _cache[analysis_id] = (meta, index)


def load(analysis_id):
    if analysis_id in _cache:
        return _cache[analysis_id]
    d = _dir(analysis_id)
    if not (d / "meta.json").exists():
        raise KeyError("Analysis not found")
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    chunks = json.loads((d / "chunks.json").read_text(encoding="utf-8"))
    vectors = np.load(d / "vectors.npy") if (d / "vectors.npy").exists() else None
    index = HybridIndex(chunks, vectors)
    _cache[analysis_id] = (meta, index)
    return meta, index
