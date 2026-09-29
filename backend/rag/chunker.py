"""
STEP 2 of RAG: split text into small overlapping "chunks" -- SECTION-AWARE.

Resumes and job descriptions have sections (Experience, Projects, Skills, Responsibilities...).
We detect those headings and never mix two sections in one chunk. Every chunk remembers its
section, which (a) tells the user WHERE evidence came from and (b) is added to the search text
so "Projects: built a RAG app" is easier to find for a question about projects.
"""
import re

SECTION_ALIASES = {
    "Summary": ["summary", "professional summary", "profile", "objective", "about me", "about the role", "about us", "overview"],
    "Education": ["education", "academic background", "qualifications"],
    "Skills": ["skills", "technical skills", "core skills", "key skills", "tech stack", "technologies", "skills and tools", "tools and technologies", "technical expertise"],
    "Experience": ["experience", "work experience", "professional experience", "employment", "internships", "internship", "work history", "internship experience"],
    "Projects": ["projects", "academic projects", "personal projects", "key projects"],
    "Certifications": ["certifications", "certificates", "courses", "licenses"],
    "Publications": ["publications", "research", "papers"],
    "Achievements": ["achievements", "awards", "achievements and activities", "activities", "extracurricular", "leadership"],
    "Responsibilities": ["responsibilities", "what you will do", "what you'll do", "role responsibilities", "key responsibilities"],
    "Requirements": ["requirements", "required qualifications", "required skills", "must have", "minimum qualifications", "who you are"],
    "Nice to have": ["nice to have", "preferred qualifications", "preferred skills", "bonus", "good to have"],
    "Benefits": ["benefits", "what we offer", "perks", "why join us"],
}
_LOOKUP = {alias: name for name, aliases in SECTION_ALIASES.items() for alias in aliases}


def detect_section(line):
    """Return a section name if this line is a heading, else None."""
    if len(line) > 45:
        return None
    base = re.sub(r"\(.*?\)", "", line)  # "Preferred qualifications (nice to have)" -> "Preferred qualifications"
    for candidate in (line, base):
        t = re.sub(r"[^a-z' ]", " ", candidate.lower().replace("&", " and "))
        t = re.sub(r"\s+", " ", t).strip()
        if t in _LOOKUP:
            return _LOOKUP[t]
    return None


def split_sections(text):
    """[(section, [lines...]), ...] -- text before the first heading is 'Header'."""
    sections, current, lines = [], "Header", []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        name = detect_section(line)
        if name:
            if lines:
                sections.append((current, lines))
            current, lines = name, []
        else:
            lines.append(line)
    if lines:
        sections.append((current, lines))
    return sections


def split_units(lines):
    units = []
    for line in lines:
        units.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line) if s.strip())
    return units


def chunk_pages(pages, source, size=500, overlap=100):
    """pages = [(page, text)] -> list of chunk dicts {id, source, page, section, text}."""
    chunks = []
    for page, text in pages:
        for section, lines in split_sections(text):
            pieces, current = [], ""
            for unit in split_units(lines):
                if current and len(current) + len(unit) + 1 > size:
                    pieces.append(current)
                    tail = current[-overlap:] if overlap else ""
                    current = tail.split(" ", 1)[-1] if " " in tail else ""  # carry the end over
                current = f"{current}\n{unit}".strip() if current else unit
            if current:
                pieces.append(current)
            chunks.extend({"source": source, "page": page, "section": section, "text": t} for t in pieces)
    for i, c in enumerate(chunks):
        c["id"] = f"{source}-{i + 1}"
    return chunks


def search_text(chunk):
    """What we actually embed / keyword-index: section name + text."""
    return f"{chunk.get('section', '')}: {chunk['text']}"
