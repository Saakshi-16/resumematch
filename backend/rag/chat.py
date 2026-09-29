"""
"Chat with your match": RAG question answering over BOTH the resume and the job description.
Retrieve -> build a numbered context -> the AI answers with citations like [1], [2].
"""
from django.conf import settings

from . import llm

SOURCE_NAMES = {"resume": "Resume", "jd": "Job Description"}

SYSTEM = (
    "You are a helpful career assistant discussing a candidate's resume and a job description.\n"
    "GROUNDING RULES:\n"
    "- FACTS about the candidate or the job (skills, experience, requirements) must come ONLY from the numbered "
    "passages or the match report. Cite passages like [1] or [2] after each factual claim.\n"
    "- You MAY reason, advise and create: interview questions, resume wording, learning plans, comparisons. "
    "Base them on the passages and the report, and cite the passages they rely on.\n"
    "- Never invent experience, employers, numbers or skills the candidate does not have.\n"
    "- Only if the question asks for a FACT that is not in the passages or report, say: "
    "\"I couldn't find that in the resume or job description.\"\n"
    "Be concise and use short bullet points when listing things."
)


def report_summary(report):
    """Short text version of the match report, so chat knows the gaps and strengths."""
    if not report:
        return ""
    lines = [f"Role: {report.get('role', '')} | Match score: {report.get('score')}%"]
    for key, label in (("matched", "Matched"), ("partial", "Partial"), ("missing", "Missing (gaps)")):
        if report.get(key):
            lines.append(f"{label}: " + "; ".join(report[key]))
    if report.get("summary"):
        lines.append("Summary: " + report["summary"])
    return "\n".join(lines)


def answer(index, question, history=None, report=None):
    sources = index.search(question, k=settings.TOP_K + 1, rerank=True)
    for n, s in enumerate(sources, start=1):
        s["n"] = n
        s["source_name"] = SOURCE_NAMES.get(s["source"], s["source"])

    if not sources:
        return {"answer": "I couldn't find anything relevant in the resume or job description.", "sources": [], "mode": "none"}

    context = "\n\n".join(
        f"[{s['n']}] ({s['source_name']}, {s.get('section', '')}, page {s['page']})\n{s['text']}" for s in sources
    )
    past = ""
    for m in (history or [])[-4:]:
        role = "User" if m.get("role") == "user" else "Assistant"
        past += f"{role}: {str(m.get('content', ''))[:500]}\n"

    summary = report_summary(report)
    prompt = f"""MATCH REPORT (from the earlier analysis):
{summary or '(not available)'}

RETRIEVED PASSAGES:
{context}

{('CONVERSATION SO FAR:' + chr(10) + past) if past else ''}
QUESTION: {question}"""

    if llm.configured():
        try:
            return {"answer": llm.generate(prompt, system=SYSTEM), "sources": sources, "mode": "ai"}
        except llm.LLMError as e:
            note = f"⚠️ {e}\n\n"
    else:
        note = "⚠️ No Gemini API key configured, so here are the most relevant passages instead of an AI answer.\n\n"

    best = "\n".join(f"- {' '.join(s['text'].split())[:250]} [{s['n']}]" for s in sources[:3])
    return {"answer": note + best, "sources": sources, "mode": "retrieval-only"}
