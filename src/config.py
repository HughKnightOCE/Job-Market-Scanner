"""
config.py - Central configuration for Job Market Scanner
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys (loaded from .env or entered via UI) ─────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
ADZUNA_APP_ID: str  = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_API_KEY: str = os.getenv("ADZUNA_API_KEY", "")

# ── Adzuna API ─────────────────────────────────────────────────────────────────
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
ADZUNA_COUNTRY_MAP = {
    "Australia":        "au",
    "United Kingdom":   "gb",
    "United States":    "us",
    "Canada":           "ca",
    "Germany":          "de",
    "France":           "fr",
    "New Zealand":      "nz",
    "Singapore":        "sg",
}

# ── RSS Remote Job Feeds ──────────────────────────────────────────────────────
# Keys are short + distinct so Streamlit multiselect doesn't truncate
RSS_FEEDS = {
    "WeWorkRemotely – All":     "https://weworkremotely.com/remote-jobs.rss",
    "WeWorkRemotely – Dev":     "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "WeWorkRemotely – Design":  "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "WeWorkRemotely – Data/AI": "https://weworkremotely.com/categories/remote-data-science-jobs.rss",
    "Remote.co":                "https://remote.co/remote-jobs/feed/",
    "Remotive":                 "https://remotive.com/remote-jobs/feed",
    "JustRemote":               "https://justremote.co/feed",
    "RemoteOK":                 "https://remoteok.com/remote-jobs.rss",
}

# ── Australian & Global Job Boards (Scraped) ──────────────────────────────────
SEEK_BASE_URL    = "https://www.seek.com.au"
JORA_BASE_URL    = "https://au.jora.com"
INDEED_BASE_URL  = "https://au.indeed.com"

SEEK_LOCATION_MAP = {
    "Australia":    "All-Australia",
    "Sydney":       "Sydney-NSW",
    "Melbourne":    "Melbourne-VIC",
    "Brisbane":     "Brisbane-QLD",
    "Perth":        "Perth-WA",
    "Adelaide":     "Adelaide-SA",
    "Canberra":     "Canberra-ACT",
    "Gold Coast":   "Gold-Coast-QLD",
    "Newcastle":    "Newcastle-NSW",
    "Ballarat":     "Ballarat-VIC",
    "Geelong":      "Geelong-VIC",
}

# Browser-like headers for scraping
SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",
}

# ── Skills Taxonomy ───────────────────────────────────────────────────────────
TECH_SKILLS = [
    # Programming Languages
    "python","javascript","typescript","java","c++","c#","go","rust","swift","kotlin",
    "php","ruby","scala","r","matlab","perl","bash","powershell","sql","nosql",
    # Web
    "react","angular","vue","svelte","nextjs","nodejs","django","flask","fastapi",
    "express","spring","asp.net","html","css","tailwind","graphql","rest","api",
    # Data / AI / ML
    "machine learning","deep learning","nlp","computer vision","tensorflow","pytorch",
    "keras","scikit-learn","pandas","numpy","spark","hadoop","data analysis",
    "data science","data engineering","etl","tableau","power bi","looker","dbt",
    "langchain","llm","ai","generative ai","rag",
    # Cloud & Infra
    "aws","azure","gcp","google cloud","docker","kubernetes","terraform","ansible",
    "ci/cd","devops","sre","linux","git","github","gitlab","jenkins","airflow",
    # Databases
    "postgresql","mysql","mongodb","redis","elasticsearch","dynamodb","snowflake",
    "bigquery","databricks","oracle","mssql",
    # Security & Networking
    "cybersecurity","penetration testing","soc","siem","firewalls","network security",
    "cisco","fortinet","palo alto","splunk","nessus","wireshark","vulnerability",
    "incident response","threat intelligence","iam","zero trust","endpoint",
    # Other Tech
    "agile","scrum","jira","confluence","product management","ux","ui",
    "figma","sketch","adobe xd","blockchain","solidity","web3","itil","itsm",
    "service desk","helpdesk","active directory","microsoft 365","office 365",
    "sharepoint","vmware","hyper-v","virtualization","windows server",
]

SOFT_SKILLS = [
    "leadership","communication","teamwork","problem solving","critical thinking",
    "time management","adaptability","creativity","collaboration","mentoring",
    "project management","stakeholder management","negotiation","presentation",
    "analytical","detail-oriented","self-motivated","remote work","customer service",
    "documentation","reporting","training","coaching",
]

ALL_SKILLS = TECH_SKILLS + SOFT_SKILLS

# ── Job Title / Role Keywords ─────────────────────────────────────────────────
JOB_TITLE_KEYWORDS = [
    "software engineer","senior software engineer","staff engineer","principal engineer",
    "software developer","full stack","frontend","backend","data scientist",
    "data engineer","data analyst","ml engineer","machine learning engineer",
    "ai engineer","devops engineer","sre","platform engineer","cloud engineer",
    "product manager","project manager","ux designer","ui designer",
    "security engineer","cybersecurity analyst","cyber security","network engineer",
    "solutions architect","architect","cto","cio","vp engineering",
    "head of engineering","tech lead","engineering manager","scrum master",
    "business analyst","systems analyst","database administrator","it manager",
    "it support","helpdesk","help desk","service desk","it technician",
    "qa engineer","test engineer","automation engineer","embedded engineer",
    "firmware engineer","desktop support","systems administrator","network administrator",
    "cloud architect","security analyst","penetration tester","soc analyst",
]

# ── Experience Level Heuristics ────────────────────────────────────────────────
EXPERIENCE_YEARS_MAP = {
    "Junior / Entry-level":  (0, 2),
    "Mid-level":             (2, 5),
    "Senior":                (5, 10),
    "Lead / Principal":      (8, 15),
    "Director / Executive":  (12, 30),
}
