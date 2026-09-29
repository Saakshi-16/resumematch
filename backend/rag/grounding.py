"""
HALLUCINATION CHECK (grounding verification).

LLMs sometimes "quote" things that are not really in the document. For every evidence quote the
AI gives, we check that it actually exists in the resume text, allowing small differences
(punctuation, spacing, a changed word) with fuzzy matching.

  similarity >= 0.80  -> verified   (the claim is grounded in the resume)
  similarity <  0.80  -> unverified (possible hallucination -> flagged and downgraded)
"""
import re
from difflib import SequenceMatcher

THRESHOLD = 0.80


def normalize(text):
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9+#%.' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def best_match(quote, document):
    """Best fuzzy similarity (0..1) of `quote` against any same-length window of `document`."""
    q, d = normalize(quote), normalize(document)
    if not q:
        return 0.0
    if q in d:
        return 1.0
    q_words, d_words = q.split(), d.split()
    n = len(q_words)
    best = 0.0
    for size in {max(1, n - 2), n, n + 2}:  # allow a couple of words added / removed
        for start in range(0, max(1, len(d_words) - size + 1)):
            window = " ".join(d_words[start:start + size])
            sm = SequenceMatcher(None, q, window, autojunk=False)
            if sm.real_quick_ratio() <= best or sm.quick_ratio() <= best:
                continue
            best = max(best, sm.ratio())
            if best > 0.98:
                return best
    return best


def verify(quote, document):
    score = best_match(quote, document)
    return {"verified": score >= THRESHOLD, "similarity": round(score, 3)}


def locate(quote, chunks):
    """Which chunk (page/section) does the quote come from?"""
    best, where = 0.0, None
    for c in chunks:
        s = best_match(quote, c["text"])
        if s > best:
            best, where = s, c
    return where
