"""
matcher.py - Matching & scoring engine
Normalised cosine + skill overlap + title boost + location preference boost.
"""

from __future__ import annotations

import re
import json
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import ALL_SKILLS, AU_SIGNALS

_vectorizer = TfidfVectorizer(
    stop_words="english", ngram_range=(1, 2),
    max_features=10000, sublinear_tf=True, min_df=1,
)


def _preprocess(text: str) -> str:
    return re.sub(r'[^a-z0-9\s]', ' ', text.lower())


def _extract_skills(text: str) -> list[str]:
    lower = text.lower()
    return [s for s in ALL_SKILLS if re.search(r'\b' + re.escape(s) + r'\b', lower)]


def _skill_match(resume_skills: list[str], job_text: str) -> tuple[list[str], list[str], float]:
    job_skills = set(_extract_skills(job_text))
    resume_set = set(s.lower() for s in resume_skills)
    matched    = [s for s in resume_set if s in job_skills]
    gaps       = [s for s in job_skills  if s not in resume_set]
    overlap    = len(matched) / len(job_skills) if job_skills else 0.0
    return matched, gaps, min(overlap, 1.0)


def _title_bonus(resume_titles: list[str], job_title: str) -> float:
    jt = job_title.lower()
    for t in resume_titles:
        if t in jt or any(w in jt for w in t.split() if len(w) > 3):
            return 0.20
    return 0.0


def _location_bonus(user_location: str, user_country: str, job: dict) -> float:
    """
    Boost AU / local jobs so they surface above generic US remote postings.
    +0.25 if the job location matches the user's city/region
    +0.15 if the job is from an AU source (Seek, Jora, etc.)
    +0.10 if the job location contains AU signals
    """
    bonus      = 0.0
    job_loc    = (job.get("location", "") + " " + job.get("source", "")).lower()
    user_loc   = user_location.lower()
    user_ctry  = user_country.lower()

    # Direct city match
    if user_loc and user_loc in job_loc:
        bonus += 0.25
    # AU source match (Seek, Jora always AU)
    if job.get("source", "") in ("Seek", "Jora", "GradConnection", "Indeed"):
        bonus += 0.15
    # AU location signal
    if any(sig in job_loc for sig in AU_SIGNALS):
        bonus += 0.10
    # Penalise jobs that say "US only" or have US-specific locations
    us_locs = ["united states", "new york", "san francisco", "california",
               "texas", "seattle", ", ny", ", ca", ", tx", ", wa us"]
    if any(ul in job_loc for ul in us_locs):
        bonus -= 0.20

    return max(bonus, -0.20)


def _cosine_scores(resume_text: str, job_texts: list[str]) -> np.ndarray:
    docs = [_preprocess(resume_text)] + [_preprocess(t) for t in job_texts]
    try:
        tfidf = _vectorizer.fit_transform(docs)
        raw   = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
        mn, mx = raw.min(), raw.max()
        return (raw - mn) / (mx - mn) if mx > mn else np.zeros(len(job_texts))
    except Exception:
        return np.zeros(len(job_texts))


def _gemini_score_batch(
    resume_profile: dict, jobs: list[dict], api_key: str, batch_size: int = 5,
) -> list[float]:
    scores: list[float] = [0.5] * len(jobs)
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        profile_str = (
            f"Skills: {', '.join(resume_profile.get('skills', [])[:30])}\n"
            f"Titles: {', '.join(resume_profile.get('job_titles', [])[:5])}\n"
            f"Experience: {resume_profile.get('experience_years', 0)} years\n"
            f"Level: {resume_profile.get('experience_level', '')}"
        )
        for start in range(0, len(jobs), batch_size):
            batch = jobs[start:start + batch_size]
            jobs_str = "\n\n".join(
                f"[{i}] {j['title']} @ {j['company']}\n{j['description'][:400]}"
                for i, j in enumerate(batch)
            )
            prompt = (
                "Rate how well each job matches this candidate (0-100).\n\n"
                f"Candidate:\n{profile_str}\n\nJobs:\n{jobs_str}\n\n"
                "Reply ONLY with a JSON integer array, e.g.: [75, 45, 90]"
            )
            resp = model.generate_content(prompt)
            raw  = re.sub(r'^```(?:json)?\s*|\s*```$', '', resp.text.strip(), flags=re.MULTILINE)
            for i, s in enumerate(json.loads(raw)[:len(batch)]):
                scores[start + i] = float(s) / 100.0
    except Exception as e:
        print(f"[Gemini scoring] {e}")
    return scores


def score_jobs(
    resume_profile: dict[str, Any],
    jobs: list[dict[str, Any]],
    gemini_api_key: str = "",
    user_location: str = "",
    user_country: str = "Australia",
) -> list[dict[str, Any]]:
    """
    Score formula (no Gemini):
      0.40 × normalised_cosine
    + 0.35 × skill_overlap
    + 0.10 × title_bonus
    + 0.15 × location_bonus   ← NEW: boosts AU / local jobs
    """
    if not jobs:
        return []

    resume_text   = resume_profile.get("raw_text", "")
    resume_skills = resume_profile.get("skills", [])
    resume_titles = resume_profile.get("job_titles", [])

    job_texts     = [j["title"] + " " + j["description"] for j in jobs]
    cos_scores    = _cosine_scores(resume_text, job_texts)
    use_gemini    = bool(gemini_api_key)
    gem_scores    = _gemini_score_batch(resume_profile, jobs, gemini_api_key) if use_gemini else [0.0] * len(jobs)

    for i, job in enumerate(jobs):
        job_text = job["title"] + " " + job["description"]
        matched, gaps, skill_overlap = _skill_match(resume_skills, job_text)
        title_bon = _title_bonus(resume_titles, job["title"])
        loc_bon   = _location_bonus(user_location, user_country, job)

        if use_gemini:
            raw = (0.20 * cos_scores[i] + 0.25 * skill_overlap
                   + 0.08 * title_bon + 0.12 * loc_bon + 0.35 * gem_scores[i])
        else:
            raw = (0.40 * cos_scores[i] + 0.35 * skill_overlap
                   + 0.10 * title_bon  + 0.15 * loc_bon)

        job["match_score"]    = round(min(max(raw * 100, 0), 99), 1)
        job["matched_skills"] = matched
        job["skill_gaps"]     = sorted(gaps)[:15]

    jobs.sort(key=lambda j: j["match_score"], reverse=True)
    return jobs


def generate_cover_letter(
    resume_profile: dict[str, Any],
    job: dict[str, Any],
    api_key: str,
    tone: str = "Professional",
) -> str:
    """Use Gemini to write a tailored cover letter for a specific job."""
    if not api_key:
        return "⚠️ A Gemini API key is required to generate cover letters. Add it in the sidebar."
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        profile_str = (
            f"Name: {resume_profile.get('name', 'Candidate')}\n"
            f"Skills: {', '.join(resume_profile.get('skills', [])[:25])}\n"
            f"Experience: {resume_profile.get('experience_years', 0)} years\n"
            f"Level: {resume_profile.get('experience_level', '')}\n"
            f"Education: {', '.join(resume_profile.get('education', []))}\n"
            f"Summary: {resume_profile.get('summary', '')[:400]}"
        )
        job_str = (
            f"Role: {job.get('title', '')}\n"
            f"Company: {job.get('company', '')}\n"
            f"Location: {job.get('location', '')}\n"
            f"Description: {job.get('description', '')[:800]}"
        )
        prompt = (
            f"Write a {tone.lower()} cover letter for this candidate applying to this job.\n\n"
            f"CANDIDATE PROFILE:\n{profile_str}\n\n"
            f"JOB:\n{job_str}\n\n"
            "Write a compelling 3-4 paragraph cover letter. "
            "Start with 'Dear Hiring Manager,' and end with 'Kind regards,' + the candidate's name. "
            "Highlight the most relevant skills and experience. Be specific, not generic."
        )
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        return f"⚠️ Cover letter generation failed: {e}"
