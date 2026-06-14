"""
scraper.py - Job listing fetcher
Supports: Adzuna REST API + multiple RSS remote job feeds.
Returns a unified list of Job dicts.
"""

from __future__ import annotations

import re
import html
import time
import hashlib
import requests
import feedparser
from datetime import datetime
from typing import Any

from src.config import (
    ADZUNA_BASE_URL, ADZUNA_COUNTRY_MAP,
    ADZUNA_APP_ID, ADZUNA_API_KEY,
    RSS_FEEDS,
)

# ── Job schema ────────────────────────────────────────────────────────────────

def _make_job(
    title: str,
    company: str,
    location: str,
    description: str,
    url: str,
    salary_min: float | None = None,
    salary_max: float | None = None,
    salary_currency: str = "AUD",
    posted_date: str = "",
    source: str = "",
    job_type: str = "Full-time",
    is_remote: bool = False,
) -> dict[str, Any]:
    job_id = hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()[:12]
    return {
        "id":              job_id,
        "title":           _clean(title),
        "company":         _clean(company),
        "location":        _clean(location),
        "description":     _clean(description),
        "url":             url,
        "salary_min":      salary_min,
        "salary_max":      salary_max,
        "salary_currency": salary_currency,
        "posted_date":     posted_date,
        "source":          source,
        "job_type":        job_type,
        "is_remote":       is_remote,
        "match_score":     0.0,
        "matched_skills":  [],
        "skill_gaps":      [],
    }


def _clean(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)   # strip HTML tags
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── Adzuna API ────────────────────────────────────────────────────────────────

def fetch_adzuna_jobs(
    keywords: list[str],
    country: str = "Australia",
    location: str = "",
    results_per_page: int = 50,
    max_pages: int = 2,
    app_id: str = "",
    api_key: str = "",
) -> list[dict[str, Any]]:
    """Fetch jobs from Adzuna API."""
    _app_id  = app_id  or ADZUNA_APP_ID
    _api_key = api_key or ADZUNA_API_KEY

    if not _app_id or not _api_key:
        return []

    country_code = ADZUNA_COUNTRY_MAP.get(country, "au")
    base = f"{ADZUNA_BASE_URL}/{country_code}/search"
    query = " ".join(keywords[:5]) if keywords else "software engineer"
    jobs: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        params: dict[str, Any] = {
            "app_id":   _app_id,
            "app_key":  _api_key,
            "results_per_page": results_per_page,
            "what":     query,
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        try:
            resp = requests.get(f"{base}/{page}", params=params, timeout=15)
            if resp.status_code != 200:
                break
            data = resp.json()
            for item in data.get("results", []):
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                jobs.append(_make_job(
                    title=item.get("title", ""),
                    company=item.get("company", {}).get("display_name", ""),
                    location=item.get("location", {}).get("display_name", ""),
                    description=item.get("description", ""),
                    url=item.get("redirect_url", ""),
                    salary_min=float(salary_min) if salary_min else None,
                    salary_max=float(salary_max) if salary_max else None,
                    salary_currency="AUD" if country_code == "au" else "USD",
                    posted_date=item.get("created", "")[:10],
                    source="Adzuna",
                    is_remote="remote" in item.get("title", "").lower()
                              or "remote" in item.get("description", "").lower(),
                ))
        except Exception as e:
            print(f"[Adzuna] Error on page {page}: {e}")
            break

        time.sleep(0.5)   # be polite

    return jobs


# ── RSS Feeds ─────────────────────────────────────────────────────────────────

def fetch_rss_jobs(
    selected_feeds: list[str] | None = None,
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from selected RSS feeds and optionally filter by keywords.
    """
    feeds_to_use = {
        k: v for k, v in RSS_FEEDS.items()
        if selected_feeds is None or k in selected_feeds
    }

    jobs: list[dict[str, Any]] = []
    kw_lower = [k.lower() for k in (keywords or [])]

    for feed_name, url in feeds_to_use.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title       = entry.get("title", "")
                description = entry.get("summary", entry.get("description", ""))
                link        = entry.get("link", "")
                published   = entry.get("published", "")[:10] if entry.get("published") else ""

                # Keyword filter (if specified)
                if kw_lower:
                    combined = (title + " " + description).lower()
                    if not any(kw in combined for kw in kw_lower):
                        continue

                # Try to extract company name from title (common format: "Title at Company")
                company = ""
                if " at " in title:
                    parts = title.rsplit(" at ", 1)
                    title   = parts[0].strip()
                    company = parts[1].strip()
                elif " @ " in title:
                    parts = title.rsplit(" @ ", 1)
                    title   = parts[0].strip()
                    company = parts[1].strip()

                jobs.append(_make_job(
                    title=title,
                    company=company,
                    location="Remote",
                    description=description,
                    url=link,
                    posted_date=published,
                    source=feed_name,
                    is_remote=True,
                ))
        except Exception as e:
            print(f"[RSS:{feed_name}] Error: {e}")
        time.sleep(0.3)

    return jobs


# ── Unified fetch ─────────────────────────────────────────────────────────────

def fetch_all_jobs(
    keywords: list[str],
    country: str = "Australia",
    location: str = "",
    include_remote: bool = True,
    include_adzuna: bool = True,
    selected_rss_feeds: list[str] | None = None,
    adzuna_app_id: str = "",
    adzuna_api_key: str = "",
) -> list[dict[str, Any]]:
    """Fetch jobs from all configured sources and deduplicate."""
    all_jobs: list[dict[str, Any]] = []

    if include_adzuna and (adzuna_app_id or ADZUNA_APP_ID):
        adzuna = fetch_adzuna_jobs(
            keywords=keywords,
            country=country,
            location=location,
            app_id=adzuna_app_id,
            api_key=adzuna_api_key,
        )
        all_jobs.extend(adzuna)

    if include_remote:
        rss = fetch_rss_jobs(
            selected_feeds=selected_rss_feeds,
            keywords=keywords if keywords else None,
        )
        all_jobs.extend(rss)

    # Deduplicate by id
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for job in all_jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            unique.append(job)

    return unique
