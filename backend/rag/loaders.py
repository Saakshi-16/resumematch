"""
STEP 1 of RAG: read the text out of uploaded files (PDF, DOCX, TXT).
Returns a list of pages: [(page_number, text), ...]
"""
import io
import re

import docx2txt
from pypdf import PdfReader

ALLOWED = (".pdf", ".docx", ".txt", ".md")


def repair_pdf_spacing(text):
    """Some PDFs insert a space after a capital letter because of letter-spacing (kerning):
    'F AISS' -> 'FAISS', 'T ools' -> 'Tools'. 'A' and 'I' are skipped because they are real words."""
    text = re.sub(r"\b([B-HJ-Z]) (?=[a-z]{2,})", r"\1", text)     # T ools  -> Tools
    text = re.sub(r"\b([B-HJ-Z]) (?=[A-Z]{2,}\b)", r"\1", text)   # F AISS  -> FAISS
    return text


def clean(text):
    text = text.replace("\x00", " ").replace("•", "-").replace("", "-")  # bullets -> dashes
    text = re.sub(r"[ \t]+", " ", text)
    text = repair_pdf_spacing(text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_pages(filename, data):
    name = filename.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        pages = [(i + 1, clean(p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    elif name.endswith(".docx"):
        pages = [(1, clean(docx2txt.process(io.BytesIO(data))))]
    elif name.endswith((".txt", ".md")):
        pages = [(1, clean(data.decode("utf-8", errors="ignore")))]
    else:
        raise ValueError(f"Unsupported file type. Please upload one of: {', '.join(ALLOWED)}")

    pages = [(n, t) for n, t in pages if t]
    if not pages:
        raise ValueError(
            f"No text found in '{filename}'. If it is a scanned/image PDF, please upload a text-based PDF or DOCX."
        )
    return pages
