"""
app.py - Job Market Scanner  |  Main Streamlit Application
"""

from __future__ import annotations

import time
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.parser        import parse_resume
from src.scraper       import fetch_all_jobs
from src.matcher       import score_jobs
from src.ui_components import (
    render_job_card, render_skill_pills, render_metrics_row,
    section_header, metric_card,
)
from src.charts import (
    match_score_histogram, salary_range_chart, top_companies_chart,
    source_pie_chart, skill_gap_chart, matched_skills_chart, match_score_gauge,
)
from src.config import RSS_FEEDS, ADZUNA_COUNTRY_MAP


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Job Market Scanner",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
  /* ── Fonts ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }

  /* ── Dark background ── */
  .stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 40%, #16213e 100%);
    min-height: 100vh;
  }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1b4b 0%, #12103a 100%);
    border-right: 1px solid #2d2b55;
  }
  [data-testid="stSidebar"] * {
    color: #c4c0e8 !important;
  }
  [data-testid="stSidebar"] .stFileUploader label,
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stTextInput label,
  [data-testid="stSidebar"] .stSlider label,
  [data-testid="stSidebar"] .stMultiSelect label {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #8b83d4 !important;
  }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    background: #1a1a2e;
    border-bottom: 1px solid #2d2b55;
    gap: 8px;
  }
  .stTabs [data-baseweb="tab"] {
    color: #64748b;
    font-weight: 600;
    border-radius: 8px 8px 0 0;
    padding: 10px 20px;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
  }

  /* ── Buttons ── */
  .stButton > button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    padding: 10px 28px !important;
    width: 100%;
    transition: opacity 0.2s;
  }
  .stButton > button:hover {
    opacity: 0.88 !important;
  }

  /* ── Form / input fields ── */
  .stTextInput input, .stSelectbox select, .stMultiSelect div {
    background: #12103a !important;
    border: 1px solid #2d2b55 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
  }

  /* ── Expanders ── */
  .streamlit-expanderHeader {
    background: #1a1a2e !important;
    border: 1px solid #2d2b55 !important;
    border-radius: 8px !important;
    color: #c4c0e8 !important;
  }
  .streamlit-expanderContent {
    background: #12103a !important;
    border: 1px solid #2d2b55 !important;
    border-top: none !important;
  }

  /* ── DataFrames ── */
  .stDataFrame { border: 1px solid #2d2b55; border-radius: 10px; overflow: hidden; }

  /* ── Scrollbars ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #1a1a2e; }
  ::-webkit-scrollbar-thumb { background: #4338ca; border-radius: 3px; }

  /* ── Plotly charts transparent background ── */
  .js-plotly-plot .plotly .main-svg { background: transparent !important; }

  /* ── Hide Streamlit branding ── */
  #MainMenu { visibility: hidden; }
  footer    { visibility: hidden; }
  header    { visibility: hidden; }

  /* ── Hero banner ── */
  .hero-banner {
    background: linear-gradient(135deg, #4338ca 0%, #7c3aed 50%, #2563eb 100%);
    border-radius: 16px;
    padding: 36px 40px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
  }
  .hero-banner::before {
    content: "";
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: rgba(255,255,255,0.05);
    border-radius: 50%;
  }
  .hero-banner h1 {
    font-size: 2rem;
    font-weight: 800;
    color: white;
    margin: 0;
  }
  .hero-banner p {
    color: rgba(255,255,255,0.75);
    margin: 8px 0 0 0;
    font-size: 1rem;
  }

  /* ── Status messages ── */
  .stSuccess, .stInfo, .stWarning, .stError {
    border-radius: 10px !important;
  }
</style>
""",
    unsafe_allow_html=True,
)


# ── Session state initialisation ──────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "resume_profile":  None,
        "jobs":            [],
        "scan_done":       False,
        "gemini_key":      "",
        "adzuna_app_id":   "",
        "adzuna_api_key":  "",
        "sort_col":        "match_score",
        "filter_score":    0,
        "filter_remote":   False,
        "filter_source":   [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
<div style="text-align:center;padding:20px 0 10px 0;">
  <div style="font-size:2.5rem;">🔭</div>
  <div style="font-size:1.1rem;font-weight:800;color:#e2e8f0;margin-top:6px;">Job Market Scanner</div>
  <div style="font-size:0.75rem;color:#64748b;">AI-powered career intelligence</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Resume upload ──────────────────────────────────────────────────────
    st.markdown("#### 📄 Your Resume")
    uploaded = st.file_uploader(
        "Upload Resume (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        help="Your resume is processed locally and never stored.",
    )

    # ── Search settings ────────────────────────────────────────────────────
    st.markdown("#### 🔍 Search Settings")

    country = st.selectbox("Country", list(ADZUNA_COUNTRY_MAP.keys()), index=0)
    location = st.text_input("City / Region (optional)", placeholder="e.g. Sydney")
    include_remote = st.toggle("Include Remote Jobs", value=True)

    rss_options = list(RSS_FEEDS.keys())
    selected_rss = st.multiselect(
        "Remote Job Feeds",
        rss_options,
        default=rss_options[:4],
    )

    min_score = st.slider("Minimum Match Score (%)", 0, 100, 0, 5)

    # ── API Keys ───────────────────────────────────────────────────────────
    with st.expander("🔑 API Keys (optional)", expanded=False):
        st.caption("Keys are stored in memory only – never saved to disk.")
        gemini_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=st.session_state.gemini_key,
            placeholder="AIza...",
        )
        adzuna_id = st.text_input(
            "Adzuna App ID",
            value=st.session_state.adzuna_app_id,
            placeholder="Your Adzuna App ID",
        )
        adzuna_key = st.text_input(
            "Adzuna API Key",
            type="password",
            value=st.session_state.adzuna_api_key,
            placeholder="Your Adzuna API Key",
        )
        if gemini_key:  st.session_state.gemini_key    = gemini_key
        if adzuna_id:   st.session_state.adzuna_app_id  = adzuna_id
        if adzuna_key:  st.session_state.adzuna_api_key = adzuna_key

    st.divider()

    # ── Scan button ────────────────────────────────────────────────────────
    scan_clicked = st.button("🚀 Scan for Jobs", use_container_width=True)

    if scan_clicked:
        if not uploaded:
            st.error("⚠️ Please upload your resume first!")
        else:
            with st.spinner("Parsing your resume…"):
                st.session_state.resume_profile = parse_resume(
                    uploaded, gemini_api_key=st.session_state.gemini_key
                )
            profile = st.session_state.resume_profile
            keywords = (profile.get("skills", [])[:10]
                        + profile.get("job_titles", [])[:3])

            with st.spinner("Fetching job listings…"):
                raw_jobs = fetch_all_jobs(
                    keywords=keywords,
                    country=country,
                    location=location,
                    include_remote=include_remote,
                    include_adzuna=bool(st.session_state.adzuna_app_id),
                    selected_rss_feeds=selected_rss if selected_rss else None,
                    adzuna_app_id=st.session_state.adzuna_app_id,
                    adzuna_api_key=st.session_state.adzuna_api_key,
                )

            with st.spinner(f"Scoring {len(raw_jobs)} jobs against your profile…"):
                scored = score_jobs(
                    resume_profile=profile,
                    jobs=raw_jobs,
                    gemini_api_key=st.session_state.gemini_key,
                )

            st.session_state.jobs     = scored
            st.session_state.scan_done = True
            st.rerun()

    if st.session_state.scan_done:
        n = len(st.session_state.jobs)
        filtered_n = len([j for j in st.session_state.jobs if j["match_score"] >= min_score])
        st.success(f"✅ {n} jobs found  •  {filtered_n} above {min_score}% match")

    # ── Clear results ──────────────────────────────────────────────────────
    if st.session_state.scan_done:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.jobs       = []
            st.session_state.scan_done  = False
            st.session_state.resume_profile = None
            st.rerun()


# ── Main content ──────────────────────────────────────────────────────────────

# Hero banner
if not st.session_state.scan_done:
    st.markdown(
        """
<div class="hero-banner">
  <h1>🔭 Job Market Scanner</h1>
  <p>Upload your resume, scan thousands of real job listings, and discover your perfect match – powered by AI.</p>
</div>
""",
        unsafe_allow_html=True,
    )
    # Instructions
    col1, col2, col3 = st.columns(3)
    steps = [
        ("📄", "1. Upload Resume", "Upload your PDF, DOCX, or TXT resume in the sidebar. Your data stays local."),
        ("⚙️", "2. Configure Search", "Select your country, location, and which job feeds to scan."),
        ("🚀", "3. Scan & Discover", "Hit 'Scan for Jobs' and let AI match you to the best opportunities."),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3], steps):
        with col:
            st.markdown(
                f"""
<div style="background:linear-gradient(135deg,#1e1b4b,#1a1a2e);border:1px solid #2d2b55;
            border-radius:14px;padding:24px;text-align:center;height:100%;">
  <div style="font-size:2.2rem;">{icon}</div>
  <div style="font-weight:700;color:#e2e8f0;margin:10px 0 6px;">{title}</div>
  <div style="font-size:0.85rem;color:#64748b;line-height:1.5;">{desc}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    # Feature highlights
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
<div style="background:linear-gradient(135deg,#1e1b4b,#1a1a2e);border:1px solid #2d2b55;
            border-radius:14px;padding:24px 32px;margin-top:8px;">
  <div style="font-size:1rem;font-weight:700;color:#8b5cf6;margin-bottom:16px;">✨ Features</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;">
    <div style="color:#94a3b8;font-size:0.85rem;">🤖 <b>AI Resume Parsing</b> – PDF, DOCX, TXT</div>
    <div style="color:#94a3b8;font-size:0.85rem;">📡 <b>Live Job Feeds</b> – RSS + Adzuna API</div>
    <div style="color:#94a3b8;font-size:0.85rem;">🎯 <b>Smart Match Scoring</b> – TF-IDF + Gemini</div>
    <div style="color:#94a3b8;font-size:0.85rem;">📊 <b>Analytics Dashboard</b> – Skill gap insights</div>
    <div style="color:#94a3b8;font-size:0.85rem;">💰 <b>Salary Intelligence</b> – Market benchmarks</div>
    <div style="color:#94a3b8;font-size:0.85rem;">🌐 <b>Remote-first</b> – Global opportunities</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.stop()


# ── Results area (after scan) ─────────────────────────────────────────────────

profile = st.session_state.resume_profile
jobs_all = st.session_state.jobs

# Filter by min score
jobs_filtered = [j for j in jobs_all if j["match_score"] >= min_score]

# ── Metrics row ────────────────────────────────────────────────────────────────
avg_score  = (sum(j["match_score"] for j in jobs_all) / len(jobs_all)) if jobs_all else 0
top_jobs   = [j for j in jobs_all if j["match_score"] >= 70]
remote_cnt = sum(1 for j in jobs_all if j.get("is_remote"))

render_metrics_row([
    ("Jobs Found",        str(len(jobs_all)),          f"{len(jobs_filtered)} above {min_score}%",  "#6366f1"),
    ("Strong Matches",    str(len(top_jobs)),           "Score ≥ 70%",                              "#22c55e"),
    ("Remote Roles",      str(remote_cnt),              f"{remote_cnt/max(len(jobs_all),1)*100:.0f}% of results", "#06b6d4"),
    ("Avg Match Score",   f"{avg_score:.1f}%",          "Across all jobs",                           "#f59e0b"),
])

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_jobs, tab_profile, tab_analytics, tab_export = st.tabs([
    "🎯  Job Listings",
    "👤  My Profile",
    "📊  Analytics",
    "📥  Export",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – JOB LISTINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_jobs:
    # Inline filters
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
    with col_f1:
        search_q = st.text_input("🔎 Search jobs", placeholder="Filter by keyword…")
    with col_f2:
        source_filter = st.multiselect(
            "Source",
            options=sorted(set(j.get("source", "") for j in jobs_all)),
            default=[],
            placeholder="All sources",
        )
    with col_f3:
        remote_only = st.toggle("Remote only", value=False)
    with col_f4:
        sort_by = st.selectbox("Sort by", ["Match Score", "Posted Date", "Company"])

    # Apply filters
    display_jobs = jobs_filtered[:]

    if search_q:
        q = search_q.lower()
        display_jobs = [
            j for j in display_jobs
            if q in j.get("title","").lower()
            or q in j.get("company","").lower()
            or q in j.get("description","").lower()
        ]

    if source_filter:
        display_jobs = [j for j in display_jobs if j.get("source") in source_filter]

    if remote_only:
        display_jobs = [j for j in display_jobs if j.get("is_remote")]

    if sort_by == "Posted Date":
        display_jobs.sort(key=lambda j: j.get("posted_date","") or "", reverse=True)
    elif sort_by == "Company":
        display_jobs.sort(key=lambda j: j.get("company","").lower())
    # Match Score is already sorted by default

    # Results count
    st.markdown(
        f'<div style="color:#64748b;font-size:0.85rem;margin:8px 0 16px 0;">'
        f'Showing <b style="color:#e2e8f0;">{len(display_jobs)}</b> jobs</div>',
        unsafe_allow_html=True,
    )

    if not display_jobs:
        st.info("🔍 No jobs match your current filters. Try lowering the minimum score or broadening your search.")
    else:
        for i, job in enumerate(display_jobs[:100]):   # cap at 100
            render_job_card(job, i)

        if len(display_jobs) > 100:
            st.info(f"Showing top 100 of {len(display_jobs)} results. Use filters to narrow down.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – MY PROFILE
# ══════════════════════════════════════════════════════════════════════════════
with tab_profile:
    if not profile:
        st.info("Upload your resume and scan to see your profile.")
    else:
        section_header("👤", "Parsed Resume Profile", "AI-extracted information from your resume")

        col_info, col_meta = st.columns([2, 1])

        with col_info:
            # Identity card
            st.markdown(
                f"""
<div style="background:linear-gradient(135deg,#1e1b4b,#1a1a2e);border:1px solid #2d2b55;
            border-radius:14px;padding:24px 28px;margin-bottom:20px;">
  <div style="font-size:1.4rem;font-weight:800;color:#e2e8f0;">{profile.get('name','Your Name')}</div>
  <div style="color:#94a3b8;margin-top:6px;">
    {"📧 " + profile.get('email','') if profile.get('email') else ''}
    {"&nbsp;&nbsp;|&nbsp;&nbsp; 📞 " + profile.get('phone','') if profile.get('phone') else ''}
  </div>
  <div style="margin-top:12px;padding-top:12px;border-top:1px solid #2d2b55;">
    <span style="background:#6366f122;color:#818cf8;border:1px solid #6366f155;
                 padding:4px 14px;border-radius:99px;font-size:0.8rem;font-weight:600;">
      {profile.get('experience_level','')}</span>
    &nbsp;
    <span style="background:#06b6d422;color:#22d3ee;border:1px solid #06b6d455;
                 padding:4px 14px;border-radius:99px;font-size:0.8rem;font-weight:600;">
      {profile.get('experience_years',0)} yrs experience</span>
    {''.join(f'&nbsp;<span style="background:#8b5cf622;color:#c4b5fd;border:1px solid #8b5cf655;padding:4px 14px;border-radius:99px;font-size:0.8rem;font-weight:600;">{e}</span>' for e in profile.get('education', []))}
  </div>
  {f'<div style="margin-top:14px;font-size:0.85rem;color:#94a3b8;line-height:1.6;">{profile.get("summary","")}</div>' if profile.get("summary") else ''}
</div>
""",
                unsafe_allow_html=True,
            )

            st.markdown("**🛠️ Technical & Soft Skills**")
            render_skill_pills(profile.get("skills", []), "#6366f1")

        with col_meta:
            # Detected titles
            st.markdown("**🎯 Target Job Titles**")
            titles = profile.get("job_titles", [])
            if titles:
                for t in titles[:8]:
                    st.markdown(
                        f'<div style="background:#1e1b4b;border:1px solid #2d2b55;border-radius:8px;'
                        f'padding:8px 12px;margin-bottom:6px;font-size:0.82rem;color:#c4c0e8;">'
                        f'🏷️ {t.title()}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No specific titles detected.")

        # Raw text preview
        with st.expander("📄 Raw extracted text preview", expanded=False):
            raw = profile.get("raw_text", "")
            st.text_area("Extracted text", raw[:3000], height=250, disabled=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    if not jobs_all:
        st.info("Run a scan first to see analytics.")
    else:
        section_header("📊", "Market Intelligence", "Insights derived from your job scan results")

        # Row 1 – Gauge + Match histogram
        col_gauge, col_hist = st.columns([1, 2])
        with col_gauge:
            st.plotly_chart(match_score_gauge(avg_score), use_container_width=True)
        with col_hist:
            st.plotly_chart(match_score_histogram(jobs_all), use_container_width=True)

        # Row 2 – Source pie + top companies
        col_pie, col_comp = st.columns(2)
        with col_pie:
            st.plotly_chart(source_pie_chart(jobs_all), use_container_width=True)
        with col_comp:
            st.plotly_chart(top_companies_chart(jobs_all), use_container_width=True)

        # Row 3 – Skill analytics
        col_match, col_gap = st.columns(2)
        with col_match:
            st.plotly_chart(matched_skills_chart(jobs_all), use_container_width=True)
        with col_gap:
            st.plotly_chart(skill_gap_chart(jobs_all), use_container_width=True)

        # Salary chart (if available)
        sal_fig = salary_range_chart(jobs_all)
        if sal_fig:
            st.plotly_chart(sal_fig, use_container_width=True)
        else:
            st.info("💰 No salary data available from current sources. Add an Adzuna API key for salary data.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – EXPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_export:
    section_header("📥", "Export Results", "Download your job matches in multiple formats")

    if not jobs_all:
        st.info("Run a scan first to export results.")
    else:
        # Build DataFrame
        df_rows = []
        for j in jobs_all:
            df_rows.append({
                "Match Score (%)":  j["match_score"],
                "Job Title":        j["title"],
                "Company":          j["company"],
                "Location":         j["location"],
                "Remote":           "Yes" if j["is_remote"] else "No",
                "Salary Min":       j.get("salary_min", ""),
                "Salary Max":       j.get("salary_max", ""),
                "Currency":         j.get("salary_currency", ""),
                "Posted Date":      j.get("posted_date", ""),
                "Source":           j.get("source", ""),
                "Matched Skills":   ", ".join(j.get("matched_skills", [])),
                "Skill Gaps":       ", ".join(j.get("skill_gaps", [])),
                "URL":              j.get("url", ""),
            })

        df = pd.DataFrame(df_rows)

        # Preview
        st.markdown("**📋 Preview** (top 20 rows)")
        st.dataframe(
            df.head(20),
            use_container_width=True,
            hide_index=True,
        )

        col_csv, col_json = st.columns(2)

        with col_csv:
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="⬇️  Download as CSV",
                data=csv_data,
                file_name="job_market_scan.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_json:
            import json as _json
            json_data = _json.dumps(jobs_all, indent=2, default=str)
            st.download_button(
                label="⬇️  Download as JSON",
                data=json_data,
                file_name="job_market_scan.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown(
            f"""
<div style="background:#1a1a2e;border:1px solid #2d2b55;border-radius:12px;
            padding:16px 24px;margin-top:16px;font-size:0.85rem;color:#94a3b8;">
  📊 <b>Export Summary</b>: {len(df)} total jobs &nbsp;|&nbsp;
  {len(df[df['Match Score (%)'] >= 70])} strong matches (≥70%) &nbsp;|&nbsp;
  {len(df[df['Remote'] == 'Yes'])} remote roles &nbsp;|&nbsp;
  {len(df['Source'].unique())} data sources
</div>
""",
            unsafe_allow_html=True,
        )
