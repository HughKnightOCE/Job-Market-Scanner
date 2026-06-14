"""
matcher.py - Matching engine
Scores each job listing against the parsed resume using TF-IDF cosine similarity
and skill overlap analysis.  Optionally enhanced by Gemini for contextual scoring.
"""

from __future__ import annotations

import re
import json
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import ALL_SKILLS


# ── TF-IDF Vectorizer (module-level, shared) ──────────────────────────────────
_vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=8000,
    sublinear_tf=True,
)


def _preprocess(text: str) -> str:
    """Lowercase, strip special chars."""
    return re.sub(r'[^a-z0-9\s]', ' ', text.lower())


# ── Skill-level matching ───────────────────────────────────────────────────────

def _extract_skills_from_text(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for skill in ALL_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, lower):
            found.append(skill)
    return found


def _skill_match(resume_skills: list[str], job_text: str) -> tuple[list[str], list[str], float]:
    """
    Returns:
        matched_skills: skills on resume that appear in job description
        skill_gaps:     skills in job description NOT on resume
        overlap_score:  0-1 float
    """
    job_skills = set(_extract_skills_from_text(job_text))
    resume_set = set(s.lower() for s in resume_skills)

    matched  = [s for s in resume_set if s in job_skills]
    gaps     = [s for s in job_skills if s not in resume_set]

    if not job_skills:
        return matched, gaps, 0.0

    overlap = len(matched) / len(job_skills)
    return matched, gaps, overlap


# ── TF-IDF cosine similarity ──────────────────────────────────────────────────

def _cosine_score(resume_text: str, job_texts: list[str]) -> np.ndarray:
    """Return an array of cosine similarity scores between resume and each job."""
    docs = [_preprocess(resume_text)] + [_preprocess(t) for t in job_texts]
    try:
        tfidf = _vectorizer.fit_transform(docs)
        scores = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
    except Exception:
        scores = np.zeros(len(job_texts))
    return scores


# ── Gemini contextual scoring ─────────────────────────────────────────────────

def _gemini_score_batch(
    resume_profile: dict[str, Any],
    jobs: list[dict[str, Any]],
    api_key: str,
    batch_size: int = 5,
) -> list[float]:
    """
    Ask Gemini to score each job 0-100 for fit against the resume.
    Returns a list of float scores 0-1.
    """
    scores: list[float] = [0.5] * len(jobs)
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        profile_str = (
            f"Skills: {', '.join(resume_profile.get('skills', [])[:30])}\n"
            f"Titles: {', '.join(resume_profile.get('job_titles', [])[:5])}\n"
            f"Experience: {resume_profile.get('experience_years', 0)} years\n"
            f"Level: {resume_profile.get('experience_level', '')}\n"
            f"Education: {', '.join(resume_profile.get('education', []))}"
        )

        for batch_start in range(0, len(jobs), batch_size):
            batch = jobs[batch_start:batch_start + batch_size]
            jobs_str = "\n\n".join(
                f"[{i}] Title: {j['title']} | Company: {j['company']}\n"
                f"Description: {j['description'][:400]}"
                for i, j in enumerate(batch)
            )

            prompt = f"""You are a career advisor. Rate how well each job matches this candidate profile (0-100).

Candidate profile:
{profile_str}

Jobs to score:
{jobs_str}

Reply ONLY with a JSON array of integers, one per job, e.g.: [75, 45, 90, 30, 60]"""

            resp = model.generate_content(prompt)
            raw = resp.text.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
            raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
            batch_scores = json.loads(raw)
            for i, score in enumerate(batch_scores[:len(batch)]):
                scores[batch_start + i] = float(score) / 100.0

    except Exception as e:
        print(f"[Gemini scoring failed: {e}]")

    return scores


# ── Main scoring function ─────────────────────────────────────────────────────

def score_jobs(
    resume_profile: dict[str, Any],
    jobs: list[dict[str, Any]],
    gemini_api_key: str = "",
    weight_cosine: float = 0.5,
    weight_skills: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Score and annotate each job with match_score, matched_skills, skill_gaps.
    If gemini_api_key is provided, uses Gemini scores (replacing cosine weight).
    Returns jobs sorted by match_score descending.
    """
    if not jobs:
        return []

    resume_text = resume_profile.get("raw_text", "")
    resume_skills = resume_profile.get("skills", [])

    # 1. Cosine similarity scores
    job_texts = [
        j["title"] + " " + j["description"]
        for j in jobs
    ]
    cosine_scores = _cosine_score(resume_text, job_texts)

    # 2. Gemini scores (optional)
    if gemini_api_key:
        gemini_scores = _gemini_score_batch(resume_profile, jobs, gemini_api_key)
        weight_cosine = 0.3
        weight_skills = 0.3
        weight_gemini = 0.4
    else:
        gemini_scores = [0.0] * len(jobs)
        weight_gemini = 0.0
        # normalize weights
        total = weight_cosine + weight_skills
        weight_cosine /= total
        weight_skills  /= total

    # 3. Annotate jobs
    for i, job in enumerate(jobs):
        matched, gaps, skill_overlap = _skill_match(resume_skills, job["description"])

        if gemini_api_key:
            final = (
                weight_cosine * cosine_scores[i]
                + weight_skills * skill_overlap
                + weight_gemini * gemini_scores[i]
            )
        else:
            final = weight_cosine * cosine_scores[i] + weight_skills * skill_overlap

        job["match_score"]   = round(min(final * 100, 100), 1)
        job["matched_skills"] = matched
        job["skill_gaps"]    = gaps[:15]   # cap for display

    # 4. Sort by match score
    jobs.sort(key=lambda j: j["match_score"], reverse=True)
    return jobs
