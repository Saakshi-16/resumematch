"""
EVALUATION -- an ablation study, like in a research paper.

We use the sample resume + job description, where the correct answers were labelled BY HAND
(a "gold" test set). Then we switch pipeline components on one at a time and measure the effect.

PART A - Chat retrieval (12 questions with a known correct passage)
PART B - Requirement evidence retrieval (does the pipeline find the right resume passage for each requirement?)
         keyword -> semantic -> hybrid -> + cross-encoder rerank -> + HyDE
PART C - Judgement accuracy: AI verdicts (match / partial / missing) vs hand-labelled gold verdicts
         accuracy, macro-F1, confusion matrix, grounding (hallucination-check) rate

Metrics
  Hit@K   : % of queries where a correct passage is in the top K
  MRR     : Mean Reciprocal Rank -- 1.0 means the correct passage is always ranked first
  nDCG@5  : rewards putting ALL correct passages near the top (1.0 = perfect ordering)
"""
import math

from . import analyzer, embedder, llm, pipeline, reranker

# ---------- PART A: chat questions ----------
QA_SET = [
    {"q": "Which programming languages does the candidate know?", "source": "resume", "expect": ["python", "c++"]},
    {"q": "Has the candidate fine-tuned a transformer model?", "source": "resume", "expect": ["distilbert"]},
    {"q": "What was the accuracy of the sentiment classifier?", "source": "resume", "expect": ["91%"]},
    {"q": "Does the candidate have leadership experience?", "source": "resume", "expect": ["technical lead", "organised"]},
    {"q": "Where did the candidate study and what is the CGPA?", "source": "resume", "expect": ["cgpa"]},
    {"q": "Has the candidate used containers?", "source": "resume", "expect": ["docker"]},
    {"q": "Which cloud services does the job require for deployment?", "source": "jd", "expect": ["aws"]},
    {"q": "Which vector databases are mentioned in the job?", "source": "jd", "expect": ["faiss", "pinecone"]},
    {"q": "Is a degree required and which graduation years are accepted?", "source": "jd", "expect": ["bachelor"]},
    {"q": "What are the nice-to-have qualifications?", "source": "jd", "expect": ["kubernetes", "mlflow"]},
    {"q": "What benefits does the company offer?", "source": "jd", "expect": ["mentorship", "learning budget"]},
    {"q": "Has the candidate built a recommendation system?", "source": "resume", "expect": ["recommend"]},
]

# ---------- PART B + C: hand-labelled requirements for the sample job ----------
GOLD = [
    {"requirement": "Strong programming skills in Python", "type": "must", "gold": "match", "expect": ["python"]},
    {"requirement": "Machine learning and NLP fundamentals", "type": "must", "gold": "match", "expect": ["distilbert", "sentiment", "nlp"]},
    {"requirement": "Hands-on experience with a deep learning framework such as PyTorch or TensorFlow", "type": "must", "gold": "match", "expect": ["pytorch"]},
    {"requirement": "Experience building REST APIs", "type": "must", "gold": "match", "expect": ["rest api"]},
    {"requirement": "Working knowledge of SQL and relational databases", "type": "must", "gold": "match", "expect": ["postgresql", "sql"]},
    {"requirement": "Familiarity with Git and collaborative development", "type": "must", "gold": "match", "expect": ["git"]},
    {"requirement": "Experience with Docker", "type": "must", "gold": "match", "expect": ["docker"]},
    {"requirement": "Good communication and teamwork skills", "type": "must", "gold": "match", "expect": ["presented", "team", "workshops"]},
    {"requirement": "Bachelor's degree in Computer Science or a related field", "type": "must", "gold": "match", "expect": ["b.e.", "computer engineering"]},
    {"requirement": "Basic frontend skills in React", "type": "nice", "gold": "match", "expect": ["react"]},
    {"requirement": "Hands-on experience with LLMs, prompt engineering or RAG", "type": "nice", "gold": "missing", "expect": []},
    {"requirement": "Experience with vector databases (FAISS, Pinecone, ChromaDB)", "type": "nice", "gold": "missing", "expect": []},
    {"requirement": "Knowledge of Kubernetes or MLOps tools such as MLflow", "type": "nice", "gold": "missing", "expect": []},
    {"requirement": "Experience deploying applications on AWS or another cloud platform", "type": "nice", "gold": "missing", "expect": []},
]

K = 3
_index = None
_resume_text = None


def _get_index():
    global _index, _resume_text
    if _index is None:
        (rn, rb), (jn, jb) = pipeline.sample_files()
        _index, _resume_text, _ = pipeline.build_index(rn, rb, jn, jb)
    return _index


def _relevant(chunk, source, expect):
    text = chunk["text"].lower()
    return chunk["source"] == source and any(e in text for e in expect)


def _metrics(runs):
    """runs = list of (ranked_results, relevance_fn, n_relevant_total)"""
    hit1 = hitk = rr = ndcg = 0.0
    for results, rel, n_rel in runs:
        flags = [rel(c) for c in results]
        first = next((i + 1 for i, f in enumerate(flags) if f), None)
        hit1 += 1 if first == 1 else 0
        hitk += 1 if first and first <= K else 0
        rr += 1.0 / first if first else 0.0
        dcg = sum(1.0 / math.log2(i + 2) for i, f in enumerate(flags[:5]) if f)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(min(5, n_rel)))
        ndcg += dcg / idcg if idcg else 0.0
    n = len(runs) or 1
    return {"hit_at_1": round(100 * hit1 / n), "hit_at_k": round(100 * hitk / n), "mrr": round(rr / n, 3), "ndcg": round(ndcg / n, 3)}


def _configs(index, with_hyde):
    configs = [("keyword", dict(mode="keyword"))]
    if index.vectors is not None:
        configs += [("semantic", dict(mode="semantic")), ("hybrid", dict(mode="hybrid"))]
    if reranker.available():
        configs.append(("hybrid + rerank", dict(mode=index.mode, rerank=True)))
    if with_hyde:
        configs.append(("hybrid + rerank + HyDE", dict(mode=index.mode, rerank=reranker.available(), hyde=True)))
    return configs


def run():
    index = _get_index()
    notes = []
    if index.vectors is None:
        notes.append("Embedding model not loaded: semantic and hybrid rows are skipped.")
    if not reranker.available():
        notes.append("Cross-encoder not loaded: rerank rows are skipped.")

    # ---- PART A ----
    qa = []
    for name, cfg in _configs(index, with_hyde=False):
        runs = []
        for case in QA_SET:
            rel = lambda c, case=case: _relevant(c, case["source"], case["expect"])  # noqa: E731
            n_rel = sum(1 for c in index.chunks if rel(c))
            runs.append((index.search(case["q"], k=10, **cfg), rel, n_rel))
        qa.append({"config": name, **_metrics(runs)})

    # ---- PART B ----
    reqs_with_evidence = [g for g in GOLD if g["expect"]]
    hyde = {}
    if llm.configured():
        lines = analyzer.hyde_queries([{"requirement": g["requirement"]} for g in reqs_with_evidence])
        hyde = {reqs_with_evidence[i]["requirement"]: t for i, t in lines.items()}
        if not hyde:
            notes.append("HyDE generation failed, so the HyDE row is skipped.")
    else:
        notes.append("No Gemini key: HyDE and judgement accuracy (Part C) are skipped.")

    req_rows = []
    for name, cfg in _configs(index, with_hyde=bool(hyde)):
        cfg = dict(cfg)
        use_hyde = cfg.pop("hyde", False)
        runs = []
        for g in reqs_with_evidence:
            rel = lambda c, g=g: _relevant(c, "resume", g["expect"])  # noqa: E731
            n_rel = sum(1 for c in index.chunks if rel(c))
            extra = [hyde.get(g["requirement"])] if use_hyde else None
            runs.append((index.search(g["requirement"], k=10, source="resume", extra_queries=extra, **cfg), rel, n_rel))
        req_rows.append({"config": name, **_metrics(runs)})

    # ---- PART C ----
    judgement = None
    if llm.configured():
        try:
            reqs = [{"requirement": g["requirement"], "type": g["type"]} for g in GOLD]
            hyde_all = {i: hyde.get(g["requirement"]) for i, g in enumerate(GOLD) if hyde.get(g["requirement"])}
            analyzer.retrieve_evidence(index, reqs, hyde=hyde_all, rerank=True)
            judged = analyzer.judge_requirements(reqs, temperature=0.0)
            analyzer.apply_judgement(reqs, judged, index, _resume_text)
            judgement = _judgement_metrics(GOLD, reqs)
        except llm.LLMError as e:
            notes.append(f"Judgement accuracy skipped: {e}")

    return {
        "k": K,
        "qa": {"n": len(QA_SET), "rows": qa},
        "requirements": {"n": len(reqs_with_evidence), "rows": req_rows},
        "judgement": judgement,
        "notes": notes,
        "components": {"embeddings": embedder.available(), "reranker": reranker.available(), "llm": llm.configured()},
    }


def _judgement_metrics(gold, predicted):
    labels = ["match", "partial", "missing"]
    matrix = {g: {p: 0 for p in labels} for g in labels}
    details = []
    for g, p in zip(gold, predicted):
        matrix[g["gold"]][p["status"]] += 1
        details.append({"requirement": g["requirement"], "gold": g["gold"], "predicted": p["status"],
                        "correct": g["gold"] == p["status"], "verified": p.get("verified")})
    n = len(gold)
    accuracy = sum(matrix[l][l] for l in labels) / n
    f1s = []
    for l in labels:
        tp = matrix[l][l]
        fp = sum(matrix[g][l] for g in labels) - tp
        fn = sum(matrix[l][p] for p in labels) - tp
        if tp + fp + fn == 0:
            continue  # class absent from both gold and predictions
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    checked = [d for d in details if d["verified"] is not None]
    return {
        "n": n,
        "accuracy": round(100 * accuracy),
        "macro_f1": round(sum(f1s) / len(f1s), 3) if f1s else 0.0,
        "grounding_rate": round(100 * sum(1 for d in checked if d["verified"]) / len(checked)) if checked else None,
        "labels": labels,
        "matrix": matrix,
        "details": details,
    }
