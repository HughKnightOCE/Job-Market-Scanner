"""
analyzer.py - Resume Gap Analysis, Career Intelligence & Salary Benchmarking
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


# ── Gap Analysis ──────────────────────────────────────────────────────────────

def analyze_gaps(
    profile: dict[str, Any],
    jobs: list[dict[str, Any]],
    gemini_api_key: str = "",
) -> dict[str, Any]:
    """
    Analyse the gap between the candidate's resume and the top matching jobs.
    Returns:
        top_missing   – [(skill, demand_count)] skills candidate lacks
        top_matched   – [(skill, demand_count)] candidate's in-demand skills
        all_demand    – Counter of every skill seen in top 30 jobs
        title_demand  – Counter of job titles in results
        gemini_report – markdown string from Gemini (if key provided)
    """
    top_jobs = sorted(jobs, key=lambda j: j["match_score"], reverse=True)[:30]

    demand: Counter = Counter()
    for job in top_jobs:
        for skill in job.get("skill_gaps", []) + job.get("matched_skills", []):
            demand[skill] += 1

    your_skills = set(s.lower() for s in profile.get("skills", []))

    top_missing = [(s, c) for s, c in demand.most_common(40) if s not in your_skills]
    top_matched = [(s, c) for s, c in demand.most_common(40) if s in your_skills]

    title_demand: Counter = Counter()
    for job in jobs:
        title_demand[job.get("title", "")[:50]] += 1

    result: dict[str, Any] = {
        "top_missing":    top_missing[:20],
        "top_matched":    top_matched[:20],
        "all_demand":     demand,
        "title_demand":   title_demand,
        "gemini_report":  "",
    }

    if gemini_api_key and jobs:
        result["gemini_report"] = _gemini_gap_report(
            profile, top_missing[:12], top_matched[:12], jobs, gemini_api_key
        )

    return result


def _gemini_gap_report(
    profile: dict[str, Any],
    missing: list[tuple[str, int]],
    matched: list[tuple[str, int]],
    jobs: list[dict[str, Any]],
    api_key: str,
) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        profile_str = (
            f"Name: {profile.get('name','Candidate')}\n"
            f"Skills: {', '.join(profile.get('skills',[])[:25])}\n"
            f"Job Titles: {', '.join(profile.get('job_titles',[]))}\n"
            f"Experience: {profile.get('experience_years',0)} yrs — {profile.get('experience_level','')}\n"
            f"Education: {', '.join(profile.get('education',[]))}"
        )
        top_jobs_str = "\n".join(
            f"  • {j['title']} @ {j['company']} ({j['match_score']:.0f}% match)"
            for j in sorted(jobs, key=lambda x: x["match_score"], reverse=True)[:10]
        )
        missing_str = ", ".join(s for s, _ in missing[:10])
        matched_str = ", ".join(s for s, _ in matched[:10])

        prompt = (
            "You are a career coach specialising in the Australian tech & IT job market. "
            "Analyse this candidate and give actionable advice.\n\n"
            f"CANDIDATE:\n{profile_str}\n\n"
            f"TOP MATCHING JOBS:\n{top_jobs_str}\n\n"
            f"IN-DEMAND SKILLS CANDIDATE HAS: {matched_str}\n"
            f"IN-DEMAND SKILLS CANDIDATE IS MISSING: {missing_str}\n\n"
            "Write a structured report with these sections (use markdown headers):\n"
            "## ✅ Strengths\n"
            "## 🎯 Priority Skill Gaps\n"
            "## 📜 Recommended Certifications\n"
            "## 📝 Resume Improvements\n"
            "## 🔍 Job Search Strategy\n\n"
            "Be specific, reference actual skills and job titles. "
            "Focus on the Australian job market (Seek, Jora, LinkedIn AU). "
            "Keep each section to 3-4 bullet points max."
        )
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        return f"*AI analysis unavailable: {e}*"


# ── Salary Benchmarking ───────────────────────────────────────────────────────

AU_TITLE_SALARIES: dict[str, tuple[int, int, int]] = {
    # (min_25th, median, max_75th) in AUD per annum
    "software engineer":         (90_000,  115_000, 145_000),
    "senior software engineer":  (120_000, 145_000, 180_000),
    "full stack":                (85_000,  110_000, 140_000),
    "data scientist":            (95_000,  120_000, 155_000),
    "data engineer":             (95_000,  120_000, 155_000),
    "ml engineer":               (110_000, 135_000, 170_000),
    "devops engineer":           (100_000, 125_000, 160_000),
    "cloud engineer":            (100_000, 125_000, 160_000),
    "cybersecurity analyst":     (85_000,  105_000, 135_000),
    "security engineer":         (95_000,  120_000, 155_000),
    "network engineer":          (75_000,  95_000,  120_000),
    "it support":                (55_000,  70_000,  90_000),
    "helpdesk":                  (50_000,  65_000,  80_000),
    "systems administrator":     (70_000,  90_000,  115_000),
    "product manager":           (105_000, 130_000, 165_000),
    "project manager":           (90_000,  110_000, 140_000),
    "solutions architect":       (130_000, 160_000, 200_000),
    "business analyst":          (85_000,  105_000, 130_000),
    "ux designer":               (80_000,  100_000, 130_000),
    "qa engineer":               (75_000,  95_000,  120_000),
    "platform engineer":         (110_000, 135_000, 170_000),
    "scrum master":              (100_000, 120_000, 148_000),
    "database administrator":    (80_000,  100_000, 130_000),
    "it manager":                (100_000, 125_000, 160_000),
}


def estimate_market_salary(profile: dict[str, Any]) -> dict[str, Any] | None:
    """
    Return estimated AU market salary based on detected job titles + experience.
    """
    titles = [t.lower() for t in profile.get("job_titles", [])]
    years  = profile.get("experience_years", 0)

    matches: list[tuple[str, tuple[int, int, int]]] = []
    for title in titles:
        for key, band in AU_TITLE_SALARIES.items():
            if key in title or title in key:
                matches.append((key, band))
                break

    if not matches:
        return None

    # Use the first match (highest priority title)
    role, (low, mid, high) = matches[0]

    # Experience bump: +4% per year over 5
    exp_factor = 1.0 + max(0, years - 5) * 0.04
    exp_factor = min(exp_factor, 1.35)

    return {
        "role":      role.title(),
        "low":       int(low  * exp_factor),
        "median":    int(mid  * exp_factor),
        "high":      int(high * exp_factor),
        "years":     years,
        "currency":  "AUD",
        "all_matches": [(r.title(), b) for r, b in matches[:5]],
    }


def benchmark_from_listings(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate salary stats directly from job listings that have salary data.
    """
    salary_jobs = [j for j in jobs if j.get("salary_max") or j.get("salary_min")]
    if not salary_jobs:
        return {"has_data": False, "count": 0}

    all_salaries = []
    by_source: dict[str, list[float]] = {}
    by_title:  dict[str, list[float]] = {}

    for job in salary_jobs:
        mid = ((job.get("salary_min") or job.get("salary_max"))
               + (job.get("salary_max") or job.get("salary_min"))) / 2
        all_salaries.append(mid)

        src = job.get("source", "Other")
        by_source.setdefault(src, []).append(mid)

        # Bucket by simplified title
        t = job.get("title", "").lower()
        bucket = "Other"
        for key in AU_TITLE_SALARIES:
            if key in t:
                bucket = key.title()
                break
        by_title.setdefault(bucket, []).append(mid)

    def _stats(vals: list[float]) -> dict[str, float]:
        s = sorted(vals)
        n = len(s)
        return {
            "min": s[0], "max": s[-1],
            "median": s[n // 2],
            "mean": sum(s) / n,
            "count": n,
        }

    return {
        "has_data":  True,
        "count":     len(salary_jobs),
        "overall":   _stats(all_salaries),
        "by_source": {k: _stats(v) for k, v in by_source.items() if len(v) >= 2},
        "by_title":  {k: _stats(v) for k, v in by_title.items()  if len(v) >= 2},
    }


# ── New-jobs tracking ─────────────────────────────────────────────────────────

def flag_new_jobs(
    jobs: list[dict[str, Any]],
    previous_ids: set[str],
) -> tuple[list[dict[str, Any]], int]:
    """
    Mark jobs with is_new=True if their ID wasn't in the previous scan.
    Returns (updated_jobs, new_count).
    """
    new_count = 0
    for job in jobs:
        job["is_new"] = job["id"] not in previous_ids
        if job["is_new"]:
            new_count += 1
    return jobs, new_count
