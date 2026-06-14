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

# ── RSS Job Feed URLs ─────────────────────────────────────────────────────────
RSS_FEEDS = {
    "We Work Remotely – All":       "https://weworkremotely.com/remote-jobs.rss",
    "We Work Remotely – Dev/Eng":   "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "We Work Remotely – Design":    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "We Work Remotely – Data/AI":   "https://weworkremotely.com/categories/remote-data-science-jobs.rss",
    "Remote.co":                    "https://remote.co/remote-jobs/feed/",
    "Remotive":                     "https://remotive.com/remote-jobs/feed",
    "JustRemote":                   "https://justremote.co/feed",
    "Remote OK":                    "https://remoteok.com/remote-jobs.rss",
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
    # Security
    "cybersecurity","penetration testing","soc","siem","firewalls","network security",
    # Other Tech
    "agile","scrum","jira","confluence","product management","ux","ui",
    "figma","sketch","adobe xd","blockchain","solidity","web3",
]

SOFT_SKILLS = [
    "leadership","communication","teamwork","problem solving","critical thinking",
    "time management","adaptability","creativity","collaboration","mentoring",
    "project management","stakeholder management","negotiation","presentation",
    "analytical","detail-oriented","self-motivated","remote work",
]

ALL_SKILLS = TECH_SKILLS + SOFT_SKILLS

# ── Job Title / Role Keywords ─────────────────────────────────────────────────
JOB_TITLE_KEYWORDS = [
    "software engineer","senior software engineer","staff engineer","principal engineer",
    "software developer","full stack","frontend","backend","data scientist",
    "data engineer","data analyst","ml engineer","machine learning engineer",
    "ai engineer","devops engineer","sre","platform engineer","cloud engineer",
    "product manager","project manager","ux designer","ui designer",
    "security engineer","cybersecurity analyst","network engineer","solutions architect",
    "architect","cto","cio","vp engineering","head of engineering","tech lead",
    "engineering manager","scrum master","business analyst","systems analyst",
    "database administrator","it manager","it support","helpdesk","qa engineer",
    "test engineer","automation engineer","embedded engineer","firmware engineer",
]

# ── Experience Level Heuristics ────────────────────────────────────────────────
EXPERIENCE_YEARS_MAP = {
    "Junior / Entry-level":  (0, 2),
    "Mid-level":             (2, 5),
    "Senior":                (5, 10),
    "Lead / Principal":      (8, 15),
    "Director / Executive":  (12, 30),
}
