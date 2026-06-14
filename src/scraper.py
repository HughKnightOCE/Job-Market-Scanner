"""
scraper.py - Job listing fetcher
Sources: Seek (AU), Jora (AU), GradConnection (AU), EthicalJobs (AU),
         Indeed AU RSS, Adzuna API, Remote RSS feeds.
"""

from __future__ import annotations

import re
import html
import json
import time
import hashlib
import requests
import feedparser
from typing import Any
from bs4 import BeautifulSoup

from src.config import (
    ADZUNA_BASE_URL, ADZUNA_COUNTRY_MAP, ADZUNA_APP_ID, ADZUNA_API_KEY,
    RSS_FEEDS, SEEK_BASE_URL, JORA_BASE_URL, INDEED_BASE_URL,
    SEEK_LOCATION_MAP, SCRAPE_HEADERS, US_ONLY_PATTERNS,
)


# ── Job schema ────────────────────────────────────────────────────────────────

def _make_job(
    title: str, company: str, location: str, description: str, url: str,
    salary_min: float | None = None, salary_max: float | None = None,
    salary_currency: str = "AUD", posted_date: str = "",
    source: str = "", job_type: str = "Full-time", is_remote: bool = False,
) -> dict[str, Any]:
    job_id = hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()[:12]
    return {
        "id": job_id, "title": _clean(title), "company": _clean(company),
        "location": _clean(location), "description": _clean(description),
        "url": url, "salary_min": salary_min, "salary_max": salary_max,
        "salary_currency": salary_currency, "posted_date": posted_date,
        "source": source, "job_type": job_type, "is_remote": is_remote,
        "match_score": 0.0, "matched_skills": [], "skill_gaps": [],
        "status": "none", "notes": "",
    }


def _clean(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _parse_salary(salary_str: str) -> tuple[float | None, float | None]:
    if not salary_str:
        return None, None
    text = salary_str.replace(",", "").replace("$", "").replace("AUD", "")
    text = re.sub(r'(\d+\.?\d*)k', lambda m: str(float(m.group(1)) * 1000), text, flags=re.I)
    nums = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', text) if float(n) >= 1000]
    if len(nums) >= 2:
        return min(nums[:2]), max(nums[:2])
    elif len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def _is_remote(title: str, desc: str, location: str) -> bool:
    combined = (title + " " + desc + " " + location).lower()
    return any(w in combined for w in ["remote", "work from home", "wfh", "distributed", "anywhere"])


def _is_us_only(title: str, desc: str) -> bool:
    """Return True if the job is explicitly US-only."""
    combined = (title + " " + desc).lower()
    return any(re.search(p, combined) for p in US_ONLY_PATTERNS)


# ── Seek ──────────────────────────────────────────────────────────────────────

def fetch_seek_jobs(
    keywords: list[str], location: str = "Australia", max_pages: int = 3,
) -> list[dict[str, Any]]:
    """Scrape Seek.com.au using data-automation HTML attributes."""
    jobs: list[dict[str, Any]] = []
    seek_location = SEEK_LOCATION_MAP.get(location, "All-Australia")

    # Build keyword slug
    kw_slug = "-".join(keywords[:4]).replace(" ", "-").lower()
    kw_slug = re.sub(r'[^a-z0-9\-]', '', kw_slug).strip("-")
    if not kw_slug:
        kw_slug = "it-jobs"

    session = requests.Session()
    session.headers.update(SCRAPE_HEADERS)

    for page in range(1, max_pages + 1):
        url    = f"{SEEK_BASE_URL}/{kw_slug}-jobs/in-{seek_location}"
        params = {"page": page} if page > 1 else {}
        try:
            resp = session.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                break
            soup  = BeautifulSoup(resp.text, "lxml")
            cards = (soup.find_all(attrs={"data-automation": "normalJob"})
                     + soup.find_all(attrs={"data-automation": "featuredJob"}))
            if not cards:
                break

            for card in cards:
                try:
                    def _da(key):
                        el = card.find(attrs={"data-automation": key})
                        return el.get_text(strip=True) if el else ""

                    title   = _da("jobTitle")
                    company = _da("jobCompany")
                    loc     = _da("jobCardLocation") or location
                    sal_txt = _da("jobSalary")
                    desc    = _da("jobShortDescription")
                    date    = _da("jobListingDate")
                    link_el = card.find("a", attrs={"data-automation": "jobTitle"})
                    href    = link_el.get("href", "") if link_el else ""
                    job_url = f"{SEEK_BASE_URL}{href.split('?')[0]}" if href else ""
                    sal_min, sal_max = _parse_salary(sal_txt)

                    if not title:
                        continue
                    jobs.append(_make_job(
                        title=title, company=company, location=loc,
                        description=desc, url=job_url,
                        salary_min=sal_min, salary_max=sal_max,
                        salary_currency="AUD", posted_date=date,
                        source="Seek", is_remote=_is_remote(title, desc, loc),
                    ))
                except Exception:
                    continue

            print(f"[Seek] Page {page}: {len(cards)} cards — total {len(jobs)}")
            time.sleep(1.5)

        except Exception as e:
            print(f"[Seek] Error p{page}: {e}")
            break

    return jobs


# ── Jora ──────────────────────────────────────────────────────────────────────

def fetch_jora_jobs(
    keywords: list[str], location: str = "Australia", max_pages: int = 3,
) -> list[dict[str, Any]]:
    """Scrape Jora AU via data-braze-job-panel-view JSON metadata."""
    jobs: list[dict[str, Any]] = []
    query   = " ".join(keywords[:5])
    session = requests.Session()
    session.headers.update(SCRAPE_HEADERS)

    for page in range(1, max_pages + 1):
        params = {
            "q": query,
            "l": "" if location == "Australia" else location,
            "p": page,
        }
        try:
            resp = session.get(f"{JORA_BASE_URL}/j", params=params, timeout=20)
            if resp.status_code != 200:
                break
            soup  = BeautifulSoup(resp.text, "lxml")
            cards = soup.find_all("div", class_=lambda c: c and "result" in c)
            if not cards:
                break

            for card in cards:
                try:
                    meta: dict = {}
                    braze = card.get("data-braze-job-panel-view", "")
                    if braze:
                        try:
                            meta = json.loads(braze)
                        except Exception:
                            pass

                    title   = meta.get("job_title", "")
                    company = meta.get("company_name", "")
                    loc     = meta.get("location", location)

                    if not title:
                        link_el = card.find("a", href=lambda h: h and "/job/" in h)
                        title   = link_el.get_text(strip=True) if link_el else ""

                    desc_el  = card.find("p") or card.find(class_=lambda c: c and "desc" in (c or ""))
                    desc     = desc_el.get_text(strip=True) if desc_el else ""
                    sal_el   = card.find(class_=lambda c: c and "salary" in (c or "").lower())
                    sal_txt  = sal_el.get_text(strip=True) if sal_el else ""
                    date_el  = card.find(class_=lambda c: c and "date" in (c or "").lower())
                    date_str = date_el.get_text(strip=True) if date_el else ""
                    link_el  = card.find("a", href=lambda h: h and "/job/" in h)
                    href     = link_el.get("href", "") if link_el else ""
                    job_url  = f"{JORA_BASE_URL}{href}" if href.startswith("/") else href
                    sal_min, sal_max = _parse_salary(sal_txt)

                    if not title:
                        continue
                    jobs.append(_make_job(
                        title=title, company=company, location=loc,
                        description=desc, url=job_url,
                        salary_min=sal_min, salary_max=sal_max,
                        salary_currency="AUD", posted_date=date_str,
                        source="Jora", is_remote=_is_remote(title, desc, loc),
                    ))
                except Exception:
                    continue

            print(f"[Jora] Page {page}: {len(cards)} cards — total {len(jobs)}")
            time.sleep(1.2)

        except Exception as e:
            print(f"[Jora] Error p{page}: {e}")
            break

    return jobs


# ── GradConnection (AU graduate jobs) ─────────────────────────────────────────

def fetch_gradconnection_jobs(
    keywords: list[str], location: str = "australia",
) -> list[dict[str, Any]]:
    """Scrape GradConnection AU."""
    jobs: list[dict[str, Any]] = []
    query = "-".join(keywords[:3]).lower()
    query = re.sub(r'[^a-z0-9\-]', '', query)
    loc_slug = location.lower().replace(" ", "-")

    urls = [
        f"https://au.gradconnection.com/jobs/search/?search={'+'.join(keywords[:4])}",
        f"https://au.gradconnection.com/graduate-jobs/information-technology/",
        f"https://au.gradconnection.com/graduate-jobs/technology/",
    ]

    session = requests.Session()
    session.headers.update(SCRAPE_HEADERS)

    for url in urls[:1]:  # just the search URL
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                continue
            soup  = BeautifulSoup(resp.text, "lxml")
            cards = soup.find_all("div", class_=lambda c: c and "job" in (c or "").lower())

            for card in cards[:20]:
                try:
                    link_el = card.find("a", href=lambda h: h and "/jobs/" in (h or ""))
                    if not link_el:
                        continue
                    title   = link_el.get_text(strip=True)
                    href    = link_el.get("href", "")
                    job_url = f"https://au.gradconnection.com{href}" if href.startswith("/") else href
                    company_el = card.find(class_=lambda c: c and "company" in (c or "").lower())
                    company    = company_el.get_text(strip=True) if company_el else ""
                    loc_el     = card.find(class_=lambda c: c and "location" in (c or "").lower())
                    loc        = loc_el.get_text(strip=True) if loc_el else location

                    if not title or len(title) < 3:
                        continue
                    jobs.append(_make_job(
                        title=title, company=company, location=loc,
                        description="", url=job_url,
                        salary_currency="AUD", source="GradConnection",
                        is_remote=_is_remote(title, "", loc),
                    ))
                except Exception:
                    continue
        except Exception as e:
            print(f"[GradConnection] Error: {e}")

    print(f"[GradConnection] {len(jobs)} jobs")
    return jobs


# ── Indeed AU RSS ─────────────────────────────────────────────────────────────

def fetch_indeed_jobs(
    keywords: list[str], location: str = "Australia", radius_km: int = 50,
) -> list[dict[str, Any]]:
    query     = " ".join(keywords[:5])
    loc_param = "" if location == "Australia" else location
    params    = {"q": query, "l": loc_param, "radius": radius_km, "fromage": 30}
    param_str = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items() if v)
    url       = f"{INDEED_BASE_URL}/rss?{param_str}"
    jobs: list[dict[str, Any]] = []
    try:
        headers = {**SCRAPE_HEADERS, "Accept": "application/rss+xml, text/xml, */*"}
        resp = requests.get(url, headers=headers, timeout=15)
        feed = feedparser.parse(resp.text)
        for entry in feed.entries[:50]:
            title   = entry.get("title", "")
            summary = _clean(entry.get("summary", ""))
            link    = entry.get("link", "")
            date    = entry.get("published", "")[:10] if entry.get("published") else ""
            company, loc = "", location
            if " - " in title:
                parts = title.split(" - ")
                if len(parts) >= 3:
                    title, company, loc = parts[0].strip(), parts[1].strip(), parts[2].strip()
                elif len(parts) == 2:
                    title, company = parts[0].strip(), parts[1].strip()
            jobs.append(_make_job(
                title=title, company=company, location=loc,
                description=summary, url=link, posted_date=date,
                source="Indeed", salary_currency="AUD",
                is_remote=_is_remote(title, summary, loc),
            ))
    except Exception as e:
        print(f"[Indeed] Error: {e}")
    return jobs


# ── Adzuna ────────────────────────────────────────────────────────────────────

def fetch_adzuna_jobs(
    keywords: list[str], country: str = "Australia", location: str = "",
    results_per_page: int = 50, max_pages: int = 2,
    app_id: str = "", api_key: str = "",
) -> list[dict[str, Any]]:
    _app_id  = app_id  or ADZUNA_APP_ID
    _api_key = api_key or ADZUNA_API_KEY
    if not _app_id or not _api_key:
        return []

    country_code = ADZUNA_COUNTRY_MAP.get(country, "au")
    base  = f"{ADZUNA_BASE_URL}/{country_code}/search"
    query = " ".join(keywords[:5]) if keywords else "it jobs"
    jobs: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        params: dict[str, Any] = {
            "app_id": _app_id, "app_key": _api_key,
            "results_per_page": results_per_page, "what": query,
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
                sal_min = item.get("salary_min")
                sal_max = item.get("salary_max")
                title   = item.get("title", "")
                desc    = item.get("description", "")
                loc     = item.get("location", {}).get("display_name", "")
                jobs.append(_make_job(
                    title=title, company=item.get("company", {}).get("display_name", ""),
                    location=loc, description=desc,
                    url=item.get("redirect_url", ""),
                    salary_min=float(sal_min) if sal_min else None,
                    salary_max=float(sal_max) if sal_max else None,
                    salary_currency="AUD" if country_code == "au" else "USD",
                    posted_date=item.get("created", "")[:10],
                    source="Adzuna", is_remote=_is_remote(title, desc, loc),
                ))
        except Exception as e:
            print(f"[Adzuna] p{page}: {e}")
            break
        time.sleep(0.5)
    return jobs


# ── RSS Feeds ─────────────────────────────────────────────────────────────────

def fetch_rss_jobs(
    selected_feeds: list[str] | None = None,
    keywords: list[str] | None = None,
    filter_us_only: bool = True,
) -> list[dict[str, Any]]:
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
                description = _clean(entry.get("summary", entry.get("description", "")))
                link        = entry.get("link", "")
                published   = entry.get("published", "")[:10] if entry.get("published") else ""

                # Skip US-only jobs
                if filter_us_only and _is_us_only(title, description):
                    continue

                # Keyword filter
                if kw_lower:
                    combined = (title + " " + description).lower()
                    if not any(kw in combined for kw in kw_lower):
                        continue

                company = ""
                if " at " in title:
                    parts = title.rsplit(" at ", 1)
                    title, company = parts[0].strip(), parts[1].strip()
                elif " @ " in title:
                    parts = title.rsplit(" @ ", 1)
                    title, company = parts[0].strip(), parts[1].strip()

                jobs.append(_make_job(
                    title=title, company=company, location="Remote (Global)",
                    description=description, url=link,
                    posted_date=published, source=feed_name, is_remote=True,
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
    include_gradconnection: bool = False,
    selected_rss_feeds: list[str] | None = None,
    adzuna_app_id: str = "",
    adzuna_api_key: str = "",
    seek_pages: int = 2,
    jora_pages: int = 2,
    filter_us_only: bool = True,
) -> list[dict[str, Any]]:
    all_jobs: list[dict[str, Any]] = []
    loc = location or country

    if include_seek and country == "Australia":
        all_jobs.extend(fetch_seek_jobs(keywords=keywords, location=location or "Australia", max_pages=seek_pages))

    if include_jora:
        all_jobs.extend(fetch_jora_jobs(keywords=keywords, location=loc, max_pages=jora_pages))

    if include_indeed:
        all_jobs.extend(fetch_indeed_jobs(keywords=keywords, location=loc))

    if include_gradconnection and country == "Australia":
        all_jobs.extend(fetch_gradconnection_jobs(keywords=keywords, location=loc))

    if include_adzuna and (adzuna_app_id or ADZUNA_APP_ID):
        all_jobs.extend(fetch_adzuna_jobs(
            keywords=keywords, country=country, location=location,
            app_id=adzuna_app_id, api_key=adzuna_api_key,
        ))

    if include_remote:
        all_jobs.extend(fetch_rss_jobs(
            selected_feeds=selected_rss_feeds,
            keywords=keywords if keywords else None,
            filter_us_only=filter_us_only,
        ))

    # Deduplicate
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for job in all_jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            unique.append(job)
    return unique
