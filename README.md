# 🔭 Job Market Scanner

An **AI-powered job board scraper & matching engine** built with Python + Streamlit.

Upload your resume and instantly discover the most relevant job opportunities from multiple live sources – scored and ranked against your profile.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📄 **Resume Parsing** | Supports PDF, DOCX, and TXT. Uses rule-based NLP or Gemini AI for extraction |
| 📡 **Live Job Feeds** | RSS feeds (We Work Remotely, Remotive, Remote.co, JustRemote, Remote OK) |
| 🔗 **Adzuna API** | Global job board API for Australia, UK, US, Canada, and more |
| 🎯 **Match Scoring** | TF-IDF cosine similarity + skill overlap scoring (Gemini-enhanced optional) |
| 📊 **Analytics Dashboard** | Match score histogram, salary charts, skill gap analysis, top companies |
| 💾 **Export** | Download results as CSV or JSON |
| 🌐 **Remote-first** | Filter and search remote roles globally |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/HughKnightOCE/job-market-scanner.git
cd job-market-scanner
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Configure API keys

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_key_here
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_API_KEY=your_adzuna_api_key
```

> **Note**: API keys can also be entered directly in the app sidebar at runtime.

### 4. Run the app

```bash
streamlit run app.py
```

Open your browser to [http://localhost:8501](http://localhost:8501).

---

## 🔑 API Keys

| API | Required | Purpose | Get it |
|---|---|---|---|
| **Gemini** | Optional | Enhanced resume parsing + contextual job scoring | [Google AI Studio](https://aistudio.google.com/) |
| **Adzuna** | Optional | Real job listings with salary data | [Adzuna Developer](https://developer.adzuna.com/) |

Without API keys, the app works fully using **free RSS job feeds** and **local TF-IDF matching**.

---

## 📁 Project Structure

```
job-market-scanner/
├── app.py                  # Main Streamlit application
├── requirements.txt
├── .env.example
├── .gitignore
└── src/
    ├── config.py           # Configuration, skills taxonomy, API URLs
    ├── parser.py           # Resume text extraction & NLP parsing
    ├── scraper.py          # Job fetching (Adzuna API + RSS feeds)
    ├── matcher.py          # TF-IDF + skill overlap matching engine
    ├── ui_components.py    # Reusable Streamlit UI components
    └── charts.py           # Plotly analytics charts
```

---

## 🧠 How Matching Works

1. **Resume parsed** → extracts skills, titles, experience, education
2. **Keywords built** from top skills + job titles
3. **Jobs fetched** from RSS feeds and/or Adzuna API
4. **TF-IDF cosine similarity** computed between resume text and each job description
5. **Skill overlap** calculated – matched skills vs gaps
6. *(Optional)* **Gemini AI** scores each job 0-100 for contextual fit
7. Final **weighted score** = `0.5 × cosine + 0.5 × skill_overlap` (or 30/30/40 with Gemini)
8. Jobs ranked by final match score descending

---

## 📸 Screenshots

> Coming soon – run the app to see it in action!

---

## 📄 License

MIT License – see [LICENSE](LICENSE)
