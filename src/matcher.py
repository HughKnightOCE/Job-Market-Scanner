"""
matcher.py - Matching engine
Scores each job listing against the parsed resume using TF-IDF cosine similarity,
title-boost, and skill overlap analysis.
Scores are normalised within each batch so results are always meaningful.
Optionally enhanced by Gemini for contextual scoring.
"""

from __future__ import annotations

import re
import json
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import ALL_SKILLS


# ── TF-IDF Vectorizer ─────────────────────────────────────────────────────────
_vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=10000,
    sublinear_tf=True,
    min_df=1,
)


def _preprocess(text: str) -> str:
    return re.sub(r'[^a-z0-9\s]', ' ', text.lower())


# ── Skill matching ─────────────────────────────────────────────────────────────

def _extract_skills_from_text(text: str) -> list[str]:
    lower = text.lower()
    return [
        skill for skill in ALL_SKILLS
        if re.search(r'\b' + re.escape(skill) + r'\b', lower)
    ]


def _skill_match(
    resume_skills: list[str], job_text: str
) -> tuple[list[str], list[str], float]:
    """Return (matched_skills, skill_gaps, overlap_score 0-1)."""
    job_skills  = set(_extract_skills_from_text(job_text))
    resume_set  = set(s.lower() for s in resume_skills)

    matched = [s for s in resume_set if s in job_skills]
    gaps    = [s for s in job_skills  if s not in resume_set]

    if not job_skills:
        return matched, gaps, 0.0

    # Jaccard-style overlap: intersection / (resume ∩ job + job gaps)
    # This rewards matching many skills in the job description
    overlap = len(matched) / len(job_skills)
    return matched, gaps, min(overlap, 1.0)


# ── TF-IDF cosine similarity ──────────────────────────────────────────────────

def _cosine_scores(resume_text: str, job_texts: list[str]) -> np.ndarray:
    """Cosine similarity; normalised to [0,1] within the batch."""
    docs = [_preprocess(resume_text)] + [_preprocess(t) for t in job_texts]
    try:
        tfidf  = _vectorizer.fit_transform(docs)
        raw    = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
        # Min-max normalise so the best job in batch gets ~1.0 cosine score
        mn, mx = raw.min(), raw.max()
        if mx > mn:
            return (raw - mn) / (mx - mn)
        return np.zeros(len(job_texts))
    except Exception:
        return np.zeros(len(job_texts))


# ── Title boost ───────────────────────────────────────────────────────────────

def _title_bonus(resume_titles: list[str], job_title: str) -> float:
    """Returns 0–0.25 bonus if the job title overlaps with candidate's titles."""
    jt_lower = job_title.lower()
    for t in resume_titles:
        if t in jt_lower or any(w in jt_lower for w in t.split()):
            return 0.25
    return 0.0


# ── Gemini contextual scoring ─────────────────────────────────────────────────

def _gemini_score_batch(
    resume_profile: dict[str, Any],
    jobs: list[dict[str, Any]],
    api_key: str,
    batch_size: int = 5,
) -> list[float]:
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

            prompt = (
                "You are a career advisor. Rate how well each job matches this candidate profile (0-100).\n\n"
                f"Candidate profile:\n{profile_str}\n\n"
                f"Jobs to score:\n{jobs_str}\n\n"
                "Reply ONLY with a JSON array of integers, one per job, e.g.: [75, 45, 90, 30, 60]"
            )

            resp = model.generate_content(prompt)
            raw  = resp.text.strip()
            raw  = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
            raw  = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
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
) -> list[dict[str, Any]]:
    """
    Score and annotate each job.  Returns jobs sorted by match_score descending.

    Scoring formula (without Gemini):
      score = 0.45 × normalised_cosine
            + 0.40 × skill_overlap
            + 0.15 × title_bonus

    With Gemini:
      score = 0.25 × normalised_cosine
            + 0.30 × skill_overlap
            + 0.10 × title_bonus
            + 0.35 × gemini_score
    """
    if not jobs:
        return []

    resume_text   = resume_profile.get("raw_text", "")
    resume_skills = resume_profile.get("skills", [])
    resume_titles = resume_profile.get("job_titles", [])

    # 1. Cosine similarity (batch-normalised)
    job_texts     = [j["title"] + " " + j["description"] for j in jobs]
    cos_scores    = _cosine_scores(resume_text, job_texts)

    # 2. Optional Gemini batch scoring
    use_gemini    = bool(gemini_api_key)
    gemini_scores = _gemini_score_batch(resume_profile, jobs, gemini_api_key) if use_gemini else [0.0] * len(jobs)

    # 3. Annotate
    for i, job in enumerate(jobs):
        job_text = job["title"] + " " + job["description"]
        matched, gaps, skill_overlap = _skill_match(resume_skills, job_text)
        title_bonus = _title_bonus(resume_titles, job["title"])

        if use_gemini:
            raw = (
                0.25 * cos_scores[i]
                + 0.30 * skill_overlap
                + 0.10 * title_bonus
                + 0.35 * gemini_scores[i]
            )
        else:
            raw = (
                0.45 * cos_scores[i]
                + 0.40 * skill_overlap
                + 0.15 * title_bonus
            )

        # Scale to percentage, cap at 99 (100 reserved for perfect Gemini match)
        job["match_score"]    = round(min(raw * 100, 99), 1)
        job["matched_skills"] = matched
        job["skill_gaps"]     = sorted(gaps)[:15]

    # 4. Sort descending
    jobs.sort(key=lambda j: j["match_score"], reverse=True)
    return jobs
