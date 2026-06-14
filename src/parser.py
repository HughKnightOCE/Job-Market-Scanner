"""
parser.py - Resume / CV parsing module
Supports PDF, DOCX, and TXT.  Optionally uses Gemini for structured extraction.
"""

from __future__ import annotations

import io
import re
import json
from pathlib import Path
from typing import Any

import pdfplumber
import docx2txt

from src.config import ALL_SKILLS, JOB_TITLE_KEYWORDS, EXPERIENCE_YEARS_MAP


# ── Raw text extraction ────────────────────────────────────────────────────────

def extract_text(uploaded_file) -> str:
    """Extract plain text from an uploaded Streamlit file object (PDF/DOCX/TXT)."""
    filename = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)   # reset for potential re-reads

    if filename.endswith(".pdf"):
        return _extract_pdf(raw_bytes)
    elif filename.endswith(".docx"):
        return _extract_docx(raw_bytes)
    elif filename.endswith(".txt"):
        return raw_bytes.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {filename}")


def _extract_pdf(raw: bytes) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_docx(raw: bytes) -> str:
    tmp = io.BytesIO(raw)
    return docx2txt.process(tmp)


# ── Rule-based parsing ────────────────────────────────────────────────────────

def parse_resume_local(text: str) -> dict[str, Any]:
    """
    Extract structured info from raw resume text using rule-based NLP.
    Returns a dict with keys: name, email, phone, skills, job_titles,
    experience_years, experience_level, education, summary.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    lower = text.lower()

    name  = _guess_name(lines)
    email = _find_email(text)
    phone = _find_phone(text)
    skills = _find_skills(lower)
    job_titles = _find_job_titles(lower)
    years = _estimate_years(text)
    level = _map_level(years)
    education = _find_education(lower)
    summary = _build_summary(lines)

    return {
        "name":             name,
        "email":            email,
        "phone":            phone,
        "skills":           skills,
        "job_titles":       job_titles,
        "experience_years": years,
        "experience_level": level,
        "education":        education,
        "summary":          summary,
        "raw_text":         text,
    }


def _guess_name(lines: list[str]) -> str:
    """Heuristic: the first short, mostly-alpha, capitalised line is the name."""
    for line in lines[:8]:
        words = line.split()
        if 1 < len(words) <= 5 and all(re.match(r"^[A-Za-z\-'\.]+$", w) for w in words):
            return line
    return "Unknown"


def _find_email(text: str) -> str:
    m = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
    return m.group() if m else ""


def _find_phone(text: str) -> str:
    m = re.search(r"(\+?\d[\d\s\-().]{7,}\d)", text)
    return m.group().strip() if m else ""


def _find_skills(lower: str) -> list[str]:
    found: list[str] = []
    for skill in ALL_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, lower):
            found.append(skill)
    # deduplicate preserving order
    return list(dict.fromkeys(found))


def _find_job_titles(lower: str) -> list[str]:
    found: list[str] = []
    for title in JOB_TITLE_KEYWORDS:
        if title in lower:
            found.append(title)
    return list(dict.fromkeys(found))


def _estimate_years(text: str) -> int:
    """Heuristic: look for 4-digit years in the text and estimate span."""
    years_found = [int(y) for y in re.findall(r'\b(19[89]\d|20[0-2]\d)\b', text)]
    if len(years_found) >= 2:
        span = max(years_found) - min(years_found)
        return min(span, 35)
    # fallback: look for explicit mentions
    m = re.search(r'(\d{1,2})\+?\s*years?\s*(of\s*)?(experience|exp)', text, re.I)
    if m:
        return int(m.group(1))
    return 0


def _map_level(years: int) -> str:
    for level, (lo, hi) in EXPERIENCE_YEARS_MAP.items():
        if lo <= years < hi:
            return level
    return "Senior" if years >= 5 else "Junior / Entry-level"


def _find_education(lower: str) -> list[str]:
    degrees = [
        "phd","doctorate","master","msc","mba","bachelor","bsc","be","beng",
        "diploma","certificate","associate","honours","hons",
    ]
    found: list[str] = []
    for deg in degrees:
        if re.search(r'\b' + re.escape(deg) + r'\b', lower):
            found.append(deg.upper())
    return list(dict.fromkeys(found))


def _build_summary(lines: list[str]) -> str:
    """Return first paragraph-like block as the professional summary."""
    summary_lines: list[str] = []
    for line in lines:
        if len(line) > 60:
            summary_lines.append(line)
            if len(summary_lines) >= 3:
                break
    return " ".join(summary_lines)[:500]


# ── Gemini-enhanced parsing ────────────────────────────────────────────────────

def parse_resume_gemini(text: str, api_key: str) -> dict[str, Any]:
    """
    Use Google Gemini to intelligently extract structured data from a resume.
    Falls back to local parsing if Gemini fails.
    """
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""You are a professional resume parser. Analyze the following resume text and extract structured information.
Return a JSON object with these exact keys:
- name (string)
- email (string)
- phone (string)
- skills (list of strings - technical AND soft skills)
- job_titles (list of strings - roles the person has held or is targeting)
- experience_years (integer - total years of professional experience)
- experience_level (string - one of: "Junior / Entry-level", "Mid-level", "Senior", "Lead / Principal", "Director / Executive")
- education (list of strings - degree types, e.g. ["BSc", "MBA"])
- summary (string - 2-3 sentence professional summary)

Resume text:
{text[:6000]}

Respond with ONLY the JSON object, no explanation."""

        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        # Strip markdown code block if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
        parsed = json.loads(raw)
        parsed["raw_text"] = text
        return parsed
    except Exception as e:
        print(f"[Gemini parse failed: {e}] Falling back to local parser.")
        return parse_resume_local(text)


# ── Unified entry point ───────────────────────────────────────────────────────

def parse_resume(uploaded_file, gemini_api_key: str = "") -> dict[str, Any]:
    """Main entry point: extract text then parse with Gemini (if key) or local."""
    text = extract_text(uploaded_file)
    if gemini_api_key:
        return parse_resume_gemini(text, gemini_api_key)
    return parse_resume_local(text)
