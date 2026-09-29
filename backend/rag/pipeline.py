"""Glue code: files -> text -> chunks -> embeddings -> index -> report."""
from django.conf import settings

from . import store
from .analyzer import build_report
from .chunker import chunk_pages
from .index import HybridIndex
from .loaders import extract_pages


def sample_files():
    resume = (settings.SAMPLE_DIR / "sample_resume.txt").read_bytes()
    jd = (settings.SAMPLE_DIR / "sample_job_description.txt").read_bytes()
    return ("sample_resume.txt", resume), ("sample_job_description.txt", jd)


def build_index(resume_name, resume_bytes, jd_name, jd_bytes):
    resume_pages = extract_pages(resume_name, resume_bytes)
    jd_pages = extract_pages(jd_name, jd_bytes)
    chunks = (
        chunk_pages(resume_pages, "resume", settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        + chunk_pages(jd_pages, "jd", settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    )
    index = HybridIndex.build(chunks)
    return index, "\n\n".join(t for _, t in resume_pages), "\n\n".join(t for _, t in jd_pages)


def analyze(resume_name, resume_bytes, jd_name, jd_bytes):
    index, resume_text, jd_text = build_index(resume_name, resume_bytes, jd_name, jd_bytes)
    report = build_report(index, resume_text, jd_text)
    analysis_id = store.new_id()
    meta = {
        "id": analysis_id,
        "resume_name": resume_name,
        "jd_name": jd_name,
        "resume_chunks": sum(1 for c in index.chunks if c["source"] == "resume"),
        "jd_chunks": sum(1 for c in index.chunks if c["source"] == "jd"),
        "jd_text": jd_text,
        "report": report,
    }
    store.save(analysis_id, meta, index)
    return meta
