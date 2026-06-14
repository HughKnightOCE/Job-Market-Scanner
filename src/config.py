"""
config.py - Central configuration for Job Market Scanner
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
ADZUNA_APP_ID: str  = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_API_KEY: str = os.getenv("ADZUNA_API_KEY", "")

# ── Adzuna ────────────────────────────────────────────────────────────────────
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
ADZUNA_COUNTRY_MAP = {
    "Australia":      "au",
    "United Kingdom": "gb",
    "United States":  "us",
    "Canada":         "ca",
    "Germany":        "de",
    "France":         "fr",
    "New Zealand":    "nz",
    "Singapore":      "sg",
}

# ── RSS Remote Job Feeds ──────────────────────────────────────────────────────
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

# ── Job Board URLs ────────────────────────────────────────────────────────────
SEEK_BASE_URL   = "https://www.seek.com.au"
JORA_BASE_URL   = "https://au.jora.com"
INDEED_BASE_URL = "https://au.indeed.com"

SEEK_LOCATION_MAP = {
    "Australia":  "All-Australia",
    "Sydney":     "Sydney-NSW",
    "Melbourne":  "Melbourne-VIC",
    "Brisbane":   "Brisbane-QLD",
    "Perth":      "Perth-WA",
    "Adelaide":   "Adelaide-SA",
    "Canberra":   "Canberra-ACT",
    "Gold Coast": "Gold-Coast-QLD",
    "Newcastle":  "Newcastle-NSW",
    "Ballarat":   "Ballarat-VIC",
    "Geelong":    "Geelong-VIC",
    "Wollongong": "Wollongong-NSW",
    "Hobart":     "Hobart-TAS",
    "Darwin":     "Darwin-NT",
    "Cairns":     "Cairns-QLD",
    "Townsville": "Townsville-QLD",
}

# ── Location signals for scoring ──────────────────────────────────────────────
AU_SIGNALS = [
    "australia", "sydney", "melbourne", "brisbane", "perth", "adelaide",
    "canberra", "gold coast", "newcastle", "wollongong", "hobart", "darwin",
    "ballarat", "geelong", "cairns", "townsville", "nsw", "vic", "qld",
    "wa", "sa", "act", "tas", "nt", "au", "seek", "jora",
]

# Patterns that indicate a job is restricted to the USA/North America
US_ONLY_PATTERNS = [
    r"\bus only\b", r"\busa only\b", r"\bunited states only\b",
    r"\bus-based\b", r"\bus residents\b", r"\bus citizens\b",
    r"\bmust.*reside.*us\b", r"\bauthorized to work in the us\b",
    r"\bwork authorization.*us\b", r"\bno.*international\b",
    r"\bnorth america only\b", r"\bcanada.*us only\b",
    r"\bhiring.*us.*canada\b",
]

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
    # IT & Support
    "active directory","microsoft 365","office 365","sharepoint","vmware",
    "hyper-v","virtualization","windows server","itil","itsm","service desk",
    "helpdesk","technical support","it support","networking","troubleshooting",
    # Other Tech
    "agile","scrum","jira","confluence","product management","ux","ui",
    "figma","sketch","adobe xd","blockchain","solidity","web3",
]

SOFT_SKILLS = [
    "leadership","communication","teamwork","problem solving","critical thinking",
    "time management","adaptability","creativity","collaboration","mentoring",
    "project management","stakeholder management","negotiation","presentation",
    "analytical","detail-oriented","self-motivated","remote work","customer service",
    "documentation","reporting","training","coaching",
]

ALL_SKILLS = TECH_SKILLS + SOFT_SKILLS

# ── Job Titles ────────────────────────────────────────────────────────────────
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

# ── Experience Levels ─────────────────────────────────────────────────────────
EXPERIENCE_YEARS_MAP = {
    "Junior / Entry-level":  (0, 2),
    "Mid-level":             (2, 5),
    "Senior":                (5, 10),
    "Lead / Principal":      (8, 15),
    "Director / Executive":  (12, 30),
}

# ── Application tracker statuses ──────────────────────────────────────────────
JOB_STATUSES = {
    "none":      ("➖", "Not saved",  "#475569"),
    "saved":     ("⭐", "Saved",      "#6366f1"),
    "applied":   ("📤", "Applied",    "#06b6d4"),
    "interview": ("📞", "Interview",  "#f59e0b"),
    "offer":     ("✅", "Offer!",     "#22c55e"),
    "rejected":  ("❌", "Rejected",   "#ef4444"),
}
