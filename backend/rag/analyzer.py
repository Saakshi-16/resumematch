"""
The core of ResumeMatch -- requirement-level RAG with verification.

  1. EXTRACT   : the AI reads the job description and lists its requirements (must-have / nice-to-have).
  2. HyDE      : for each requirement the AI writes a HYPOTHETICAL resume line that would satisfy it.
                 Searching with that line bridges the vocabulary gap between job-ad language and resume language.
  3. RETRIEVE  : two-stage retrieval per requirement: hybrid search (requirement + HyDE line) -> cross-encoder rerank.
  4. JUDGE     : the AI marks each requirement match / partial / missing using ONLY the retrieved evidence.
  5. VERIFY    : every quote is checked against the real resume text (hallucination check).
  6. SCORE     : calculated in Python (not by the AI) so it is consistent and explainable.

If the AI is not configured or fails, a keyword-based backup produces the report instead.
"""
import numpy as np

from . import grounding, llm, skills
from .index import HybridIndex

EXTRACT_SYSTEM = (
    "You are an expert technical recruiter. Extract the hiring requirements from a job description. "
    "Only use what is written in the job description."
)
HYDE_SYSTEM = "You write realistic, specific resume bullet points."
JUDGE_SYSTEM = (
    "You are a fair, strict recruiter comparing a candidate's resume to job requirements. "
    "For each requirement you are given EVIDENCE retrieved from the resume. Judge ONLY from that evidence; "
    "never assume skills that are not shown. Quote evidence EXACTLY as written in the evidence (copy-paste, no paraphrasing)."
)


# ---------- 1. requirements ----------
def extract_requirements(jd_text):
    prompt = f"""Read this job description and extract 8 to 12 key requirements.

Return JSON exactly like:
{{"role": "job title", "requirements": [
  {{"requirement": "short requirement, e.g. Strong Python programming", "type": "must" or "nice", "category": "skill" | "experience" | "education" | "soft skill"}}
]}}

"must" = required qualification/responsibility. "nice" = preferred / nice to have.

JOB DESCRIPTION:
\"\"\"{jd_text[:12000]}\"\"\""""
    data = llm.generate(prompt, system=EXTRACT_SYSTEM, as_json=True)
    reqs = []
    for r in data.get("requirements", [])[:12]:
        text = str(r.get("requirement", "")).strip()
        if text:
            reqs.append({
                "requirement": text,
                "type": "nice" if str(r.get("type", "")).lower().startswith("nice") else "must",
                "category": str(r.get("category", "skill")).lower(),
            })
    if not reqs:
        raise llm.LLMError("The AI could not find requirements in the job description.")
    return str(data.get("role", "")).strip() or "the role", reqs


# ---------- 2. HyDE ----------
def hyde_queries(reqs):
    """One LLM call -> a hypothetical resume bullet for every requirement. Returns {index: text}."""
    listing = "\n".join(f"{n}. {r['requirement']}" for n, r in enumerate(reqs, start=1))
    prompt = f"""For each job requirement below, write ONE realistic resume bullet point (max 25 words)
that a candidate who meets the requirement might have on their resume. Use concrete tools and actions.

{listing}

Return JSON exactly like: {{"lines": [{{"id": 1, "text": "..."}}]}}"""
    try:
        data = llm.generate(prompt, system=HYDE_SYSTEM, as_json=True, temperature=0.3)
        return {int(x["id"]) - 1: str(x.get("text", "")) for x in data.get("lines", []) if str(x.get("id", "")).isdigit()}
    except (llm.LLMError, KeyError, ValueError, TypeError):
        return {}  # HyDE is an enhancement: if it fails we just search with the requirement alone


# ---------- 3. retrieve ----------
def retrieve_evidence(index, reqs, hyde=None, rerank=True, k=3):
    for n, req in enumerate(reqs):
        extra = [hyde[n]] if hyde and hyde.get(n) else None
        req["evidence_chunks"] = index.search(req["requirement"], k=k, source="resume", rerank=rerank, extra_queries=extra)
    return reqs


# ---------- 4. judge ----------
def judge_requirements(reqs, temperature=0.2):
    blocks = []
    for n, req in enumerate(reqs, start=1):
        ev = "\n".join(
            f"  - [{c.get('section', '')}, page {c['page']}] {c['text'][:450]}" for c in req.get("evidence_chunks", [])
        ) or "  - (nothing relevant found)"
        blocks.append(f"REQUIREMENT {n} [{req['type']}]: {req['requirement']}\nEVIDENCE FROM RESUME:\n{ev}")

    prompt = f"""Evaluate each requirement using only its evidence.

{chr(10).join(blocks)}

Return JSON exactly like:
{{
 "assessments": [{{"id": 1, "status": "match" | "partial" | "missing", "evidence": "exact short quote copied from the evidence, or empty", "reason": "one sentence"}}],
 "summary": "2-3 sentence overall assessment of the candidate for this role",
 "strengths": ["3 short strengths"],
 "suggestions": [{{"requirement": "a partial or missing requirement", "suggestion": "a concrete, honest action or resume bullet the candidate could add"}}]
}}
Rules: "match" = clearly demonstrated. "partial" = related or basic experience only. "missing" = no evidence.
The evidence quote must be copied word-for-word from the evidence (max 25 words).
Give 3-5 suggestions focused on the most important gaps. Never invent experience the candidate does not have."""
    return llm.generate(prompt, system=JUDGE_SYSTEM, as_json=True, temperature=temperature)


def apply_judgement(reqs, judged, index, resume_text):
    """Merge AI verdicts into the requirement list + run the hallucination check."""
    by_id = {int(a.get("id", 0)): a for a in judged.get("assessments", []) if str(a.get("id", "")).isdigit()}
    resume_chunks = [c for c in index.chunks if c["source"] == "resume"]
    for n, r in enumerate(reqs, start=1):
        a = by_id.get(n, {})
        status = str(a.get("status", "missing")).lower()
        r["status"] = status if status in ("match", "partial", "missing") else "missing"
        r["evidence"] = str(a.get("evidence", "")).strip()[:300]
        r["reason"] = str(a.get("reason", ""))
        top = r.pop("evidence_chunks", [])
        r["retrieved"] = [
            {"section": c.get("section"), "page": c["page"], "rerank": c.get("rerank"), "text": c["text"][:200]} for c in top
        ]
        r["verified"], r["similarity"], r["page"], r["section"] = None, None, None, None

        if r["status"] != "missing":
            if r["evidence"]:
                check = grounding.verify(r["evidence"], resume_text)
                r["verified"], r["similarity"] = check["verified"], check["similarity"]
                where = grounding.locate(r["evidence"], resume_chunks) if check["verified"] else None
            else:
                r["verified"], r["similarity"], where = False, 0.0, None
            where = where or (top[0] if top else None)
            if where:
                r["page"], r["section"] = where["page"], where.get("section")
            if r["verified"] is False and r["status"] == "match":
                r["status"] = "partial"  # don't trust a match we can't verify
                r["reason"] = (r["reason"] + " (Downgraded: the quoted evidence could not be found in the resume.)").strip()
    return reqs


# ---------- Backup (no AI) ----------
def keyword_report(index, jd_text):
    jd_skills = skills.find_skills(jd_text)
    resume_chunks = [c for c in index.chunks if c["source"] == "resume"]
    reqs = []
    for s in jd_skills:
        hit = next((c for c in resume_chunks if any(skills._has(c["text"].lower(), a) for a in skills.aliases_for(s))), None)
        reqs.append({
            "requirement": s, "type": "must", "category": "skill",
            "status": "match" if hit else "missing",
            "evidence": hit["text"][:220] if hit else "",
            "page": hit["page"] if hit else None,
            "section": hit.get("section") if hit else None,
            "verified": True if hit else None,
            "reason": "Mentioned in the resume." if hit else "Not mentioned in the resume.",
            "retrieved": [],
        })
    missing = [r["requirement"] for r in reqs if r["status"] == "missing"]
    return {
        "role": "the role",
        "requirements": reqs,
        "summary": f"Keyword analysis found {len(reqs)} skills in the job description; "
                   f"{len(reqs) - len(missing)} of them appear in the resume.",
        "strengths": [r["requirement"] for r in reqs if r["status"] == "match"][:3],
        "suggestions": [{"requirement": m, "suggestion": f"If you have experience with {m}, add a project or bullet that shows it; otherwise consider a short course or mini-project."} for m in missing[:5]],
    }


# ---------- Score ----------
def compute_score(reqs):
    weights = {"must": 2.0, "nice": 1.0}
    values = {"match": 1.0, "partial": 0.5, "missing": 0.0}
    total = sum(weights[r["type"]] for r in reqs)
    got = sum(weights[r["type"]] * values.get(r["status"], 0) for r in reqs)
    return round(100 * got / total) if total else 0


def semantic_similarity(index):
    if index.vectors is None:
        return None
    src = np.array([c["source"] for c in index.chunks])
    if not (src == "resume").any() or not (src == "jd").any():
        return None
    a = index.vectors[src == "resume"].mean(axis=0)
    b = index.vectors[src == "jd"].mean(axis=0)
    return round(float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b))) * 100)


def grounding_rate(reqs):
    checked = [r for r in reqs if r.get("verified") is not None]
    if not checked:
        return None
    return round(100 * sum(1 for r in checked if r["verified"]) / len(checked))


# ---------- Main entry point ----------
def build_report(index: HybridIndex, resume_text, jd_text):
    from . import reranker

    warnings, report, pipeline = [], None, []
    if llm.configured():
        try:
            role, reqs = extract_requirements(jd_text)
            hyde = hyde_queries(reqs)
            retrieve_evidence(index, reqs, hyde=hyde, rerank=True)
            judged = judge_requirements(reqs)
            apply_judgement(reqs, judged, index, resume_text)
            report = {
                "role": role, "requirements": reqs,
                "summary": judged.get("summary", ""),
                "strengths": judged.get("strengths", [])[:5],
                "suggestions": judged.get("suggestions", [])[:5],
                "mode": "ai",
            }
            pipeline = ["Requirement extraction (LLM)", "HyDE query expansion" if hyde else "HyDE skipped",
                        "Hybrid search (BM25 + embeddings, RRF)",
                        "Cross-encoder reranking" if reranker.available() else "Reranking skipped",
                        "LLM judgement", "Hallucination check"]
        except llm.LLMError as e:
            warnings.append(f"{e} Showing keyword-based analysis instead.")
    else:
        warnings.append("No Gemini API key configured, so this is a keyword-based analysis. Add a key for the full AI analysis.")

    if report is None:
        report = keyword_report(index, jd_text)
        report["mode"] = "keyword"
        pipeline = ["Skill keyword matching"]

    reqs = report["requirements"]
    report["score"] = compute_score(reqs)
    report["semantic_similarity"] = semantic_similarity(index)
    report["grounding_rate"] = grounding_rate(reqs) if report["mode"] == "ai" else None
    report["matched"] = [r["requirement"] for r in reqs if r["status"] == "match"]
    report["partial"] = [r["requirement"] for r in reqs if r["status"] == "partial"]
    report["missing"] = [r["requirement"] for r in reqs if r["status"] == "missing"]
    report["retrieval_mode"] = index.mode
    report["pipeline"] = pipeline
    report["warnings"] = warnings
    return report
