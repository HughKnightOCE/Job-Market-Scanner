"""
scraper.py - Job listing fetcher
Sources: Seek (AU), Jora (AU), Indeed AU RSS, Adzuna API, Remote RSS feeds.
Returns a unified list of Job dicts.
"""

from __future__ import annotations

import re
import html
import json
import time
import hashlib
import requests
import feedparser
from datetime import datetime
from typing import Any
from bs4 import BeautifulSoup

from src.config import (
    ADZUNA_BASE_URL, ADZUNA_COUNTRY_MAP,
    ADZUNA_APP_ID, ADZUNA_API_KEY,
    RSS_FEEDS,
    SEEK_BASE_URL, JORA_BASE_URL, INDEED_BASE_URL,
    SEEK_LOCATION_MAP, SCRAPE_HEADERS,
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
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _parse_salary_text(salary_str: str) -> tuple[float | None, float | None]:
    """Parse salary text like 'AUD 140000 - 160000 per annum' or '$100k - $120k'."""
    if not salary_str:
        return None, None
    text = salary_str.replace(",", "").replace("$", "").replace("AUD", "")
    # Convert k notation
    text = re.sub(r'(\d+\.?\d*)k', lambda m: str(float(m.group(1)) * 1000), text, flags=re.I)
    nums = re.findall(r'\d+(?:\.\d+)?', text)
    nums = [float(n) for n in nums if float(n) >= 1000]  # ignore small numbers
    if len(nums) >= 2:
        return min(nums[:2]), max(nums[:2])
    elif len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def _is_remote(title: str, desc: str, location: str) -> bool:
    combined = (title + " " + desc + " " + location).lower()
    return any(w in combined for w in ["remote", "work from home", "wfh", "distributed", "anywhere"])


# ── Seek Scraper ──────────────────────────────────────────────────────────────

def fetch_seek_jobs(
    keywords: list[str],
    location: str = "Australia",
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    """
    Scrape Seek.com.au job listings using their data-automation HTML attributes.
    Seek renders content server-side so requests + BeautifulSoup works.
    """
    jobs: list[dict[str, Any]] = []

    # Build slug for location
    seek_location = SEEK_LOCATION_MAP.get(location, "All-Australia")
    # Build keyword slug: replace spaces with hyphens
    keyword_parts = "-".join(keywords[:4]).replace(" ", "-").lower()
    keyword_parts = re.sub(r'[^a-z0-9\-]', '', keyword_parts)

    session = requests.Session()
    session.headers.update(SCRAPE_HEADERS)

    for page in range(1, max_pages + 1):
        url = f"{SEEK_BASE_URL}/{keyword_parts}-jobs/in-{seek_location}"
        params = {"page": page} if page > 1 else {}

        try:
            resp = session.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                print(f"[Seek] HTTP {resp.status_code} on page {page}")
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Seek uses data-automation="normalJob" for standard listings
            cards = soup.find_all(attrs={"data-automation": "normalJob"})
            # Also grab featured jobs
            cards += soup.find_all(attrs={"data-automation": "featuredJob"})

            if not cards:
                print(f"[Seek] No cards found on page {page}, stopping.")
                break

            for card in cards:
                try:
                    title_el    = card.find(attrs={"data-automation": "jobTitle"})
                    company_el  = card.find(attrs={"data-automation": "jobCompany"})
                    loc_el      = card.find(attrs={"data-automation": "jobCardLocation"})
                    salary_el   = card.find(attrs={"data-automation": "jobSalary"})
                    desc_el     = card.find(attrs={"data-automation": "jobShortDescription"})
                    date_el     = card.find(attrs={"data-automation": "jobListingDate"})
                    link_el     = card.find("a", attrs={"data-automation": "jobTitle"})

                    title    = title_el.get_text(strip=True)    if title_el    else ""
                    company  = company_el.get_text(strip=True)  if company_el  else ""
                    loc      = loc_el.get_text(strip=True)      if loc_el      else location
                    sal_text = salary_el.get_text(strip=True)   if salary_el   else ""
                    desc     = desc_el.get_text(strip=True)     if desc_el     else ""
                    date_str = date_el.get_text(strip=True)     if date_el     else ""
                    href     = link_el.get("href", "")          if link_el     else ""

                    job_url = f"{SEEK_BASE_URL}{href.split('?')[0]}" if href else ""
                    sal_min, sal_max = _parse_salary_text(sal_text)

                    if not title:
                        continue

                    jobs.append(_make_job(
                        title=title,
                        company=company,
                        location=loc,
                        description=desc,
                        url=job_url,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        salary_currency="AUD",
                        posted_date=date_str,
                        source="Seek",
                        is_remote=_is_remote(title, desc, loc),
                    ))
                except Exception as e:
                    continue

            print(f"[Seek] Page {page}: {len(cards)} cards found, total so far: {len(jobs)}")
            time.sleep(1.5)  # be polite

        except Exception as e:
            print(f"[Seek] Error on page {page}: {e}")
            break

    return jobs


# ── Jora Scraper ──────────────────────────────────────────────────────────────

def fetch_jora_jobs(
    keywords: list[str],
    location: str = "Australia",
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    """
    Scrape Jora AU job listings. Jora stores job data in data-braze-job-panel-view JSON
    attributes on each job card div.
    """
    jobs: list[dict[str, Any]] = []
    query = " ".join(keywords[:5])
    session = requests.Session()
    session.headers.update(SCRAPE_HEADERS)

    for page in range(1, max_pages + 1):
        params = {
            "q": query,
            "l": location if location != "Australia" else "",
            "p": page,
        }

        try:
            resp = session.get(f"{JORA_BASE_URL}/j", params=params, timeout=20)
            if resp.status_code != 200:
                print(f"[Jora] HTTP {resp.status_code} on page {page}")
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Jora job cards have data-braze-job-panel-view with JSON metadata
            cards = soup.find_all("div", class_=lambda c: c and "result" in c)

            if not cards:
                print(f"[Jora] No cards on page {page}, stopping.")
                break

            for card in cards:
                try:
                    # Extract JSON metadata from data attribute
                    braze_data = card.get("data-braze-job-panel-view", "")
                    meta: dict = {}
                    if braze_data:
                        try:
                            meta = json.loads(braze_data)
                        except Exception:
                            pass

                    title   = meta.get("job_title", "")
                    company = meta.get("company_name", "")
                    loc     = meta.get("location", "")
                    job_id  = meta.get("job_id", "")

                    # Fallback: extract from HTML
                    if not title:
                        link_el = card.find("a", href=lambda h: h and "/job/" in h)
                        title   = link_el.get_text(strip=True) if link_el else ""

                    # Get short description from the card HTML
                    desc_el = card.find("p", class_=lambda c: c and "description" in (c or ""))
                    if not desc_el:
                        desc_el = card.find("p")
                    desc = desc_el.get_text(strip=True) if desc_el else ""

                    # Get salary
                    sal_el = card.find(class_=lambda c: c and "salary" in (c or "").lower())
                    sal_text = sal_el.get_text(strip=True) if sal_el else ""
                    sal_min, sal_max = _parse_salary_text(sal_text)

                    # Get posted date
                    date_el = card.find(class_=lambda c: c and "date" in (c or "").lower())
                    date_str = date_el.get_text(strip=True) if date_el else ""

                    # Build URL
                    link_el = card.find("a", href=lambda h: h and "/job/" in h)
                    href = link_el.get("href", "") if link_el else ""
                    job_url = f"{JORA_BASE_URL}{href}" if href.startswith("/") else href

                    if not title:
                        continue

                    jobs.append(_make_job(
                        title=title,
                        company=company,
                        location=loc or location,
                        description=desc,
                        url=job_url,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        salary_currency="AUD",
                        posted_date=date_str,
                        source="Jora",
                        is_remote=_is_remote(title, desc, loc),
                    ))
                except Exception as e:
                    continue

            print(f"[Jora] Page {page}: {len(cards)} cards, total: {len(jobs)}")
            time.sleep(1.2)

        except Exception as e:
            print(f"[Jora] Error on page {page}: {e}")
            break

    return jobs


# ── Indeed AU RSS ─────────────────────────────────────────────────────────────

def fetch_indeed_jobs(
    keywords: list[str],
    location: str = "Australia",
    radius_km: int = 50,
    max_entries: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from Indeed AU via their public RSS feed.
    """
    query = " ".join(keywords[:5])
    params = {
        "q":      query,
        "l":      location if location != "Australia" else "",
        "radius": radius_km,
        "limit":  max_entries,
        "fromage": 30,  # posted in last 30 days
    }
    param_str = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items() if v)
    url = f"{INDEED_BASE_URL}/rss?{param_str}"

    jobs: list[dict[str, Any]] = []
    try:
        headers = {**SCRAPE_HEADERS, "Accept": "application/rss+xml, application/xml, text/xml, */*"}
        resp = requests.get(url, headers=headers, timeout=15)
        feed = feedparser.parse(resp.text)

        for entry in feed.entries[:max_entries]:
            title   = entry.get("title", "")
            summary = _clean(entry.get("summary", ""))
            link    = entry.get("link", "")
            date    = entry.get("published", "")[:10] if entry.get("published") else ""

            # Indeed title format: "Job Title - Company Name - Location"
            company = ""
            loc     = location
            if " - " in title:
                parts = title.split(" - ")
                if len(parts) >= 3:
                    title   = parts[0].strip()
                    company = parts[1].strip()
                    loc     = parts[2].strip()
                elif len(parts) == 2:
                    title   = parts[0].strip()
                    company = parts[1].strip()

            jobs.append(_make_job(
                title=title,
                company=company,
                location=loc,
                description=summary,
                url=link,
                posted_date=date,
                source="Indeed",
                salary_currency="AUD",
                is_remote=_is_remote(title, summary, loc),
            ))
    except Exception as e:
        print(f"[Indeed] Error: {e}")

    return jobs


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
            "app_id":           _app_id,
            "app_key":          _api_key,
            "results_per_page": results_per_page,
            "what":             query,
            "content-type":     "application/json",
        }
        if location:
            params["where"] = location

        try:
            resp = requests.get(f"{base}/{page}", params=params, timeout=15)
            if resp.status_code != 200:
                break
            data = resp.json()
            for item in data.get("results", []):
                sal_min = item.get("salary_min")
                sal_max = item.get("salary_max")
                jobs.append(_make_job(
                    title=item.get("title", ""),
                    company=item.get("company", {}).get("display_name", ""),
                    location=item.get("location", {}).get("display_name", ""),
                    description=item.get("description", ""),
                    url=item.get("redirect_url", ""),
                    salary_min=float(sal_min) if sal_min else None,
                    salary_max=float(sal_max) if sal_max else None,
                    salary_currency="AUD" if country_code == "au" else "USD",
                    posted_date=item.get("created", "")[:10],
                    source="Adzuna",
                    is_remote=_is_remote(
                        item.get("title",""),
                        item.get("description",""),
                        item.get("location",{}).get("display_name",""),
                    ),
                ))
        except Exception as e:
            print(f"[Adzuna] Error on page {page}: {e}")
            break
        time.sleep(0.5)

    return jobs


# ── RSS Feeds ─────────────────────────────────────────────────────────────────

def fetch_rss_jobs(
    selected_feeds: list[str] | None = None,
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from selected RSS feeds with optional keyword filter.
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

                # Keyword filter
                if kw_lower:
                    combined = (title + " " + description).lower()
                    if not any(kw in combined for kw in kw_lower):
                        continue

                # Parse "Title at Company" / "Title @ Company"
                company = ""
                if " at " in title:
                    parts = title.rsplit(" at ", 1)
                    title, company = parts[0].strip(), parts[1].strip()
                elif " @ " in title:
                    parts = title.rsplit(" @ ", 1)
                    title, company = parts[0].strip(), parts[1].strip()

                jobs.append(_make_job(
                    title=title,
                    company=company,
                    location="Remote",
                    description=_clean(description),
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
    include_seek: bool = True,
    include_jora: bool = True,
    include_indeed: bool = True,
    include_adzuna: bool = True,
    selected_rss_feeds: list[str] | None = None,
    adzuna_app_id: str = "",
    adzuna_api_key: str = "",
    seek_pages: int = 2,
    jora_pages: int = 2,
) -> list[dict[str, Any]]:
    """Fetch jobs from all configured sources and deduplicate."""
    all_jobs: list[dict[str, Any]] = []
    loc = location or country

    # ── Australian/Global scraped boards ──
    if include_seek and country == "Australia":
        seek_loc = location if location else "Australia"
        seek_jobs = fetch_seek_jobs(keywords=keywords, location=seek_loc, max_pages=seek_pages)
        all_jobs.extend(seek_jobs)

    if include_jora:
        jora_jobs = fetch_jora_jobs(keywords=keywords, location=loc, max_pages=jora_pages)
        all_jobs.extend(jora_jobs)

    if include_indeed:
        indeed_jobs = fetch_indeed_jobs(keywords=keywords, location=loc)
        all_jobs.extend(indeed_jobs)

    if include_adzuna and (adzuna_app_id or ADZUNA_APP_ID):
        adzuna = fetch_adzuna_jobs(
            keywords=keywords,
            country=country,
            location=location,
            app_id=adzuna_app_id,
            api_key=adzuna_api_key,
        )
        all_jobs.extend(adzuna)

    # ── Remote RSS feeds ──
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
