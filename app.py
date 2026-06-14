"""
app.py - Job Market Scanner  |  Main Streamlit Application
"""

from __future__ import annotations

import json as _json
import pandas as pd
import streamlit as st

from src.parser        import parse_resume
from src.scraper       import fetch_all_jobs
from src.matcher       import score_jobs, generate_cover_letter
from src.ui_components import (
    render_job_card, render_skill_pills, render_metrics_row, section_header,
)
from src.charts import (
    match_score_histogram, salary_range_chart, top_companies_chart,
    source_pie_chart, skill_gap_chart, matched_skills_chart, match_score_gauge,
)
from src.config import RSS_FEEDS, ADZUNA_COUNTRY_MAP, JOB_STATUSES
from src.analyzer import (
    analyze_gaps, estimate_market_salary, benchmark_from_listings, flag_new_jobs,
)
from src.pdf_export import generate_pdf
import time


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Market Scanner",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 40%, #16213e 100%);
    min-height: 100vh;
  }

  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1b4b 0%, #12103a 100%);
    border-right: 1px solid #2d2b55;
  }
  [data-testid="stSidebar"] * { color: #c4c0e8 !important; }
  [data-testid="stSidebar"] label {
    font-size: 0.78rem !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: 0.05em; color: #8b83d4 !important;
  }

  .stTabs [data-baseweb="tab-list"] {
    background: #1a1a2e; border-bottom: 1px solid #2d2b55; gap: 6px;
  }
  .stTabs [data-baseweb="tab"] {
    color: #64748b; font-weight: 600; border-radius: 8px 8px 0 0; padding: 10px 16px;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important;
  }

  .stButton > button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    font-weight: 700 !important; transition: opacity 0.2s;
  }
  .stButton > button:hover { opacity: 0.88 !important; }

  .streamlit-expanderHeader {
    background: #1a1a2e !important; border: 1px solid #2d2b55 !important;
    border-radius: 8px !important; color: #c4c0e8 !important;
  }
  .streamlit-expanderContent {
    background: #12103a !important; border: 1px solid #2d2b55 !important; border-top: none !important;
  }

  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #1a1a2e; }
  ::-webkit-scrollbar-thumb { background: #4338ca; border-radius: 3px; }

  .js-plotly-plot .plotly .main-svg { background: transparent !important; }
  #MainMenu { visibility: hidden; }
  footer    { visibility: hidden; }
  header    { visibility: hidden; }

  .hero-banner {
    background: linear-gradient(135deg, #4338ca 0%, #7c3aed 50%, #2563eb 100%);
    border-radius: 16px; padding: 36px 40px; margin-bottom: 28px;
    position: relative; overflow: hidden;
  }
  .hero-banner::before {
    content: ""; position: absolute; top: -50%; right: -10%;
    width: 300px; height: 300px; background: rgba(255,255,255,0.05); border-radius: 50%;
  }
  .hero-banner h1 { font-size: 2rem; font-weight: 800; color: white; margin: 0; }
  .hero-banner p  { color: rgba(255,255,255,0.75); margin: 8px 0 0 0; font-size: 1rem; }

  /* Status tracker badge */
  .status-badge {
    display: inline-block; padding: 4px 12px; border-radius: 99px;
    font-size: 0.75rem; font-weight: 700; margin: 2px;
  }
  /* Cover letter output */
  .cover-letter-box {
    background: #12103a; border: 1px solid #2d2b55; border-radius: 12px;
    padding: 24px 28px; font-size: 0.9rem; color: #e2e8f0; line-height: 1.8;
    white-space: pre-wrap; font-family: 'Inter', sans-serif;
  }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "resume_profile": None, "jobs": [], "scan_done": False,
        "gemini_key": "", "adzuna_app_id": "", "adzuna_api_key": "",
        "job_statuses": {},   # {job_id: status_key}
        "job_notes": {},      # {job_id: note_text}
        "cover_letter": "",
        "cover_letter_job_id": "",
        "last_location": "",
        "last_country": "Australia",
        "gap_report": "",
        "last_scan_time": 0.0,
        "trigger_autoscan": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="text-align:center;padding:20px 0 12px 0;">
  <div style="font-size:2.5rem;">🔭</div>
  <div style="font-size:1.1rem;font-weight:800;color:#e2e8f0;margin-top:6px;">Job Market Scanner</div>
  <div style="font-size:0.75rem;color:#64748b;">AI-powered career intelligence</div>
</div>""", unsafe_allow_html=True)
    st.divider()

    st.markdown("#### 📄 Your Resume")
    uploaded = st.file_uploader(
        "Upload Resume (PDF, DOCX, TXT)", type=["pdf","docx","txt"],
        help="Processed locally – never stored.",
    )

    st.markdown("#### 🌏 Location")
    country  = st.selectbox("Country", list(ADZUNA_COUNTRY_MAP.keys()), index=0)
    location = st.text_input("City / Region", placeholder="e.g. Ballarat, Melbourne…",
                             value=st.session_state.last_location)

    st.markdown("#### 📡 Job Sources")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        inc_seek   = st.checkbox("🔵 Seek",   value=True,  help="Seek.com.au")
        inc_jora   = st.checkbox("🟣 Jora",   value=True,  help="Jora.com.au")
        inc_indeed = st.checkbox("🔴 Indeed", value=True,  help="Indeed AU RSS")
    with col_s2:
        inc_remote = st.checkbox("🌐 Remote", value=True,  help="Remote RSS feeds")
        inc_adzuna = st.checkbox("🟠 Adzuna", value=False, help="Requires API key")
        inc_grad   = st.checkbox("🎓 Grad",   value=False, help="GradConnection AU")

    if inc_seek or inc_jora:
        pages = st.slider("Pages per board", 1, 5, 2)
    else:
        pages = 2

    if inc_remote:
        with st.expander("Remote RSS feeds", expanded=False):
            rss_opts    = list(RSS_FEEDS.keys())
            selected_rss = st.multiselect("Feeds", rss_opts, default=rss_opts[:4],
                                          label_visibility="collapsed")
    else:
        selected_rss = []

    filter_us = st.toggle("🚫 Filter US-only jobs", value=True,
                          help="Remove jobs explicitly restricted to US residents")

    st.markdown("#### 🎯 Filter")
    min_score = st.slider("Minimum Match Score (%)", 0, 100, 0, 5)

    st.markdown("#### ⏰ Auto-Scan")
    auto_scan_opt = st.selectbox(
        "Auto-Scan Interval",
        ["Disabled", "10 Minutes", "30 Minutes", "60 Minutes"],
        index=0,
        help="Runs job scan automatically in the background if the dashboard is kept open.",
    )

    interval_mins = 0
    if auto_scan_opt == "10 Minutes":
        interval_mins = 10
    elif auto_scan_opt == "30 Minutes":
        interval_mins = 30
    elif auto_scan_opt == "60 Minutes":
        interval_mins = 60

    with st.expander("🔑 API Keys (optional)"):
        st.caption("Stored in memory only.")
        gemini_key = st.text_input("Gemini API Key", type="password",
                                   value=st.session_state.gemini_key, placeholder="AIza…")
        adzuna_id  = st.text_input("Adzuna App ID",  value=st.session_state.adzuna_app_id)
        adzuna_key = st.text_input("Adzuna API Key", type="password",
                                   value=st.session_state.adzuna_api_key)
        if gemini_key: st.session_state.gemini_key    = gemini_key
        if adzuna_id:  st.session_state.adzuna_app_id  = adzuna_id
        if adzuna_key: st.session_state.adzuna_api_key = adzuna_key

    st.divider()

    scan_clicked = st.button("🚀 Scan for Jobs", use_container_width=True)

    # Check if auto-scan is triggered
    if st.session_state.scan_done and interval_mins > 0 and st.session_state.get("last_scan_time"):
        elapsed = (time.time() - st.session_state.last_scan_time) / 60
        if elapsed >= interval_mins:
            st.session_state.trigger_autoscan = True

    if scan_clicked or (st.session_state.get("trigger_autoscan") and st.session_state.resume_profile):
        st.session_state.trigger_autoscan = False
        
        if scan_clicked and not uploaded and not st.session_state.resume_profile:
            st.error("Please upload your resume first!")
        elif not any([inc_seek, inc_jora, inc_indeed, inc_remote, inc_adzuna, inc_grad]):
            st.error("Select at least one job source!")
        else:
            st.session_state.last_location = location
            st.session_state.last_country  = country

            if scan_clicked or not st.session_state.resume_profile:
                with st.spinner("Parsing your resume…"):
                    st.session_state.resume_profile = parse_resume(
                        uploaded, gemini_api_key=st.session_state.gemini_key)

            profile  = st.session_state.resume_profile
            keywords = profile.get("skills", [])[:10] + profile.get("job_titles", [])[:3]

            with st.spinner(f"Fetching jobs from selected sources…"):
                raw_jobs = fetch_all_jobs(
                    keywords=keywords, country=country, location=location,
                    include_seek=inc_seek, include_jora=inc_jora,
                    include_indeed=inc_indeed, include_remote=inc_remote,
                    include_adzuna=inc_adzuna and bool(st.session_state.adzuna_app_id),
                    include_gradconnection=inc_grad,
                    selected_rss_feeds=selected_rss if selected_rss else None,
                    adzuna_app_id=st.session_state.adzuna_app_id,
                    adzuna_api_key=st.session_state.adzuna_api_key,
                    seek_pages=pages, jora_pages=pages,
                    filter_us_only=filter_us,
                )

            with st.spinner(f"Scoring {len(raw_jobs)} jobs…"):
                scored = score_jobs(
                    resume_profile=profile, jobs=raw_jobs,
                    gemini_api_key=st.session_state.gemini_key,
                    user_location=location, user_country=country,
                )

            # Restore saved statuses/notes
            for job in scored:
                jid = job["id"]
                job["status"] = st.session_state.job_statuses.get(jid, "none")
                job["notes"]  = st.session_state.job_notes.get(jid, "")

            # If we had a previous list, we can flag new jobs
            prev_ids = {j["id"] for j in st.session_state.jobs} if st.session_state.jobs else set()
            if prev_ids:
                scored, new_cnt = flag_new_jobs(scored, prev_ids)
                if new_cnt > 0:
                    st.toast(f"🔔 Found {new_cnt} new jobs!", icon="🎉")

            st.session_state.jobs      = scored
            st.session_state.scan_done = True
            st.session_state.gap_report = ""  # reset gap report on new scan
            st.session_state.last_scan_time = time.time()
            st.rerun()

    if st.session_state.scan_done:
        n = len(st.session_state.jobs)
        f = len([j for j in st.session_state.jobs if j["match_score"] >= min_score])
        st.success(f"{n} jobs found  •  {f} above {min_score}%")
        
        # Countdown reload handler
        if interval_mins > 0 and st.session_state.last_scan_time:
            elapsed = (time.time() - st.session_state.last_scan_time) / 60
            if elapsed < interval_mins:
                remaining_sec = int((interval_mins - elapsed) * 60)
                st.sidebar.info(f"⏰ Next auto-scan in {remaining_sec // 60}m {remaining_sec % 60}s")
                
                import streamlit.components.v1 as components
                js_code = f"""
                <a id="refresh-link" href="/" target="_parent" style="display:none;">Refresh</a>
                <script>
                  setTimeout(function() {{
                    var link = document.getElementById("refresh-link");
                    link.click();
                  }}, {remaining_sec * 1000});
                </script>
                """
                components.html(js_code, height=0, width=0)

    if st.session_state.scan_done:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.jobs = []; st.session_state.scan_done = False
            st.session_state.resume_profile = None; st.rerun()


# ── Landing page ──────────────────────────────────────────────────────────────
if not st.session_state.scan_done:
    st.markdown("""
<div class="hero-banner">
  <h1>🔭 Job Market Scanner</h1>
  <p>Upload your resume, scan live job listings across Seek, Jora, Indeed &amp; more — AI-ranked for your profile.</p>
</div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    steps = [
        ("📄", "1. Upload Resume",    "PDF, DOCX, or TXT. Stays local, never uploaded."),
        ("⚙️", "2. Pick Sources",     "Seek, Jora, Indeed, remote feeds — your choice."),
        ("🚀", "3. Scan & Match",     "AI scores every job against your profile instantly."),
    ]
    for col, (icon, title, desc) in zip([c1,c2,c3], steps):
        with col:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1e1b4b,#1a1a2e);border:1px solid #2d2b55;'
                f'border-radius:14px;padding:24px;text-align:center;">'
                f'<div style="font-size:2.2rem;">{icon}</div>'
                f'<div style="font-weight:700;color:#e2e8f0;margin:10px 0 6px;">{title}</div>'
                f'<div style="font-size:0.85rem;color:#64748b;line-height:1.5;">{desc}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
<div style="background:linear-gradient(135deg,#1e1b4b,#1a1a2e);border:1px solid #2d2b55;border-radius:14px;padding:24px 32px;">
  <div style="font-size:1rem;font-weight:700;color:#8b5cf6;margin-bottom:16px;">✨ Features</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;">
    <div style="color:#94a3b8;font-size:0.85rem;">🔵 <b>Seek.com.au</b> — Australia's #1 board</div>
    <div style="color:#94a3b8;font-size:0.85rem;">🟣 <b>Jora.com.au</b> — AU aggregated jobs</div>
    <div style="color:#94a3b8;font-size:0.85rem;">🔴 <b>Indeed AU</b> — local + global listings</div>
    <div style="color:#94a3b8;font-size:0.85rem;">🌐 <b>Remote feeds</b> — WeWorkRemotely, Remotive</div>
    <div style="color:#94a3b8;font-size:0.85rem;">📋 <b>Application Tracker</b> — track every job</div>
    <div style="color:#94a3b8;font-size:0.85rem;">💌 <b>Cover Letter AI</b> — Gemini-powered</div>
    <div style="color:#94a3b8;font-size:0.85rem;">📊 <b>Analytics</b> — salary &amp; skill gap insights</div>
    <div style="color:#94a3b8;font-size:0.85rem;">🚫 <b>US-filter</b> — hides US-only remote roles</div>
  </div>
</div>""", unsafe_allow_html=True)
    st.stop()


# ── Results ───────────────────────────────────────────────────────────────────
profile       = st.session_state.resume_profile
jobs_all      = st.session_state.jobs
jobs_filtered = [j for j in jobs_all if j["match_score"] >= min_score]
avg_score     = sum(j["match_score"] for j in jobs_all) / len(jobs_all) if jobs_all else 0
top_jobs      = [j for j in jobs_all if j["match_score"] >= 70]
remote_cnt    = sum(1 for j in jobs_all if j.get("is_remote"))
au_cnt        = sum(1 for j in jobs_all if j.get("source") in ("Seek", "Jora", "GradConnection", "Indeed"))
sources       = set(j.get("source","") for j in jobs_all)

render_metrics_row([
    ("Jobs Found",      str(len(jobs_all)),    f"{len(jobs_filtered)} above {min_score}%",          "#6366f1"),
    ("AU Jobs",         str(au_cnt),           "Seek · Jora · Indeed",                              "#22c55e"),
    ("Strong Matches",  str(len(top_jobs)),    "Score ≥ 70%",                                       "#06b6d4"),
    ("Avg Match Score", f"{avg_score:.1f}%",   f"Across {len(sources)} source(s)",                  "#f59e0b"),
])

st.markdown("<br>", unsafe_allow_html=True)

tab_jobs, tab_tracker, tab_cover, tab_gaps, tab_profile, tab_analytics, tab_export = st.tabs([
    "🎯  Job Listings",
    "📋  Application Tracker",
    "💌  Cover Letter",
    "🔍  Gap Analysis",
    "👤  My Profile",
    "📊  Analytics",
    "📥  Export",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – JOB LISTINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_jobs:
    cf1, cf2, cf3, cf4, cf5 = st.columns([2, 1.5, 1, 1, 1])
    with cf1:
        search_q = st.text_input("Search", placeholder="Filter by keyword…", label_visibility="collapsed")
    with cf2:
        source_filter = st.multiselect(
            "Source", options=sorted(sources), default=[], placeholder="All sources",
            label_visibility="collapsed",
        )
    with cf3:
        remote_only = st.toggle("Remote only")
    with cf4:
        au_only = st.toggle("AU only", help="Show only Seek/Jora/Indeed jobs")
    with cf5:
        sort_by = st.selectbox("Sort", ["Match Score","Posted Date","Company"],
                               label_visibility="collapsed")

    display = jobs_filtered[:]
    if search_q:
        q = search_q.lower()
        display = [j for j in display if q in (j.get("title","") + j.get("company","") + j.get("description","")).lower()]
    if source_filter:
        display = [j for j in display if j.get("source") in source_filter]
    if remote_only:
        display = [j for j in display if j.get("is_remote")]
    if au_only:
        display = [j for j in display if j.get("source") in ("Seek","Jora","GradConnection","Indeed")]
    if sort_by == "Posted Date":
        display.sort(key=lambda j: j.get("posted_date","") or "", reverse=True)
    elif sort_by == "Company":
        display.sort(key=lambda j: j.get("company","").lower())

    st.markdown(
        f'<div style="color:#64748b;font-size:0.85rem;margin:8px 0 16px 0;">'
        f'Showing <b style="color:#e2e8f0;">{len(display)}</b> of {len(jobs_all)} jobs</div>',
        unsafe_allow_html=True,
    )

    if not display:
        st.info("No jobs match your filters. Try lowering the minimum score or enabling more sources.")
    else:
        for i, job in enumerate(display[:100]):
            render_job_card(job, i, session_state=st.session_state)
        if len(display) > 100:
            st.info(f"Showing top 100 of {len(display)}. Use filters to narrow down.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – APPLICATION TRACKER
# ══════════════════════════════════════════════════════════════════════════════
with tab_tracker:
    section_header("📋", "Application Tracker", "Track every job you've saved or applied to")

    if not jobs_all:
        st.info("Scan for jobs first.")
    else:
        # Status summary row
        status_counts = {}
        for key, (icon, label, colour) in JOB_STATUSES.items():
            if key == "none":
                continue
            count = sum(1 for j in jobs_all if st.session_state.job_statuses.get(j["id"],"none") == key)
            status_counts[key] = (icon, label, colour, count)

        cols = st.columns(len(status_counts))
        for col, (key, (icon, label, colour, count)) in zip(cols, status_counts.items()):
            with col:
                st.markdown(
                    f'<div style="background:#1e1b4b;border:1px solid {colour}55;border-top:3px solid {colour};'
                    f'border-radius:12px;padding:14px;text-align:center;">'
                    f'<div style="font-size:1.6rem;font-weight:800;color:{colour};">{count}</div>'
                    f'<div style="font-size:0.8rem;color:#94a3b8;">{icon} {label}</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # Tracked jobs table
        tracked = [j for j in jobs_all
                   if st.session_state.job_statuses.get(j["id"],"none") != "none"]

        if not tracked:
            st.info("No jobs tracked yet. Open any job card in **Job Listings** and set a status.")
        else:
            for job in tracked:
                jid    = job["id"]
                status = st.session_state.job_statuses.get(jid, "none")
                icon, label, colour = JOB_STATUSES[status][:3]

                with st.container():
                    st.markdown(
                        f'<div style="background:#1e1b4b;border:1px solid #2d2b55;border-left:4px solid {colour};'
                        f'border-radius:10px;padding:14px 18px;margin-bottom:10px;">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                        f'<div>'
                        f'<span style="font-weight:700;color:#e2e8f0;">{job["title"]}</span>'
                        f'<span style="color:#64748b;font-size:0.82rem;"> — {job.get("company","")}</span>'
                        f'<span style="margin-left:8px;background:{colour}22;color:{colour};border:1px solid {colour}55;'
                        f'padding:2px 10px;border-radius:99px;font-size:0.72rem;font-weight:700;">{icon} {label}</span>'
                        f'</div>'
                        f'<span style="color:#f59e0b;font-weight:700;">{job["match_score"]:.0f}%</span>'
                        f'</div>'
                        f'<div style="font-size:0.78rem;color:#64748b;margin-top:4px;">'
                        f'📍 {job.get("location","")}  •  {job.get("source","")}  •  {job.get("posted_date","")}'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

                    tc1, tc2, tc3 = st.columns([2, 2, 1])
                    with tc1:
                        new_status = st.selectbox(
                            "Status", list(JOB_STATUSES.keys()),
                            index=list(JOB_STATUSES.keys()).index(status),
                            format_func=lambda k: f"{JOB_STATUSES[k][0]} {JOB_STATUSES[k][1]}",
                            key=f"tracker_status_{jid}",
                            label_visibility="collapsed",
                        )
                        if new_status != status:
                            st.session_state.job_statuses[jid] = new_status
                            job["status"] = new_status
                            st.rerun()
                    with tc2:
                        note = st.text_input(
                            "Notes", value=st.session_state.job_notes.get(jid,""),
                            placeholder="Add a note…", key=f"tracker_note_{jid}",
                            label_visibility="collapsed",
                        )
                        st.session_state.job_notes[jid] = note
                    with tc3:
                        st.markdown(
                            f'<a href="{job.get("url","#")}" target="_blank" style="display:inline-block;'
                            f'padding:8px 16px;background:linear-gradient(90deg,#6366f1,#8b5cf6);'
                            f'color:white;border-radius:8px;text-decoration:none;font-weight:600;font-size:0.82rem;">Apply</a>',
                            unsafe_allow_html=True,
                        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – COVER LETTER GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_cover:
    section_header("💌", "Cover Letter Generator", "AI-powered personalised cover letters via Gemini")

    if not st.session_state.gemini_key:
        st.warning("A Gemini API key is required. Add it in the sidebar under API Keys.")
    elif not profile:
        st.info("Upload your resume and run a scan first.")
    elif not jobs_all:
        st.info("Scan for jobs first.")
    else:
        cl_col1, cl_col2 = st.columns([2, 1])
        with cl_col1:
            job_options = {f"{j['title']} @ {j['company']} ({j['match_score']:.0f}%)": j
                          for j in jobs_all[:50]}
            selected_label = st.selectbox("Select a job", list(job_options.keys()))
            selected_job   = job_options[selected_label]
        with cl_col2:
            tone = st.selectbox("Tone", ["Professional", "Enthusiastic", "Concise", "Creative"])

        if st.button("✨ Generate Cover Letter", use_container_width=True):
            with st.spinner("Writing your cover letter…"):
                letter = generate_cover_letter(
                    resume_profile=profile,
                    job=selected_job,
                    api_key=st.session_state.gemini_key,
                    tone=tone,
                )
            st.session_state.cover_letter        = letter
            st.session_state.cover_letter_job_id = selected_job["id"]

        if st.session_state.cover_letter:
            st.markdown(f'<div class="cover-letter-box">{st.session_state.cover_letter}</div>',
                        unsafe_allow_html=True)
            st.download_button(
                "⬇️  Download as .txt", st.session_state.cover_letter,
                file_name="cover_letter.txt", mime="text/plain",
                use_container_width=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3.5 – RESUME GAP ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_gaps:
    section_header("🔍", "Resume Gap Analysis", "Compare your resume skills with market demands")
    
    if not profile:
        st.info("Upload your resume and scan to see your gap analysis.")
    elif not jobs_all:
        st.info("Scan for jobs first.")
    else:
        # Run gap analysis (no Gemini call if api_key not provided)
        with st.spinner("Analyzing skill gaps…"):
            gaps = analyze_gaps(profile, jobs_all, gemini_api_key="")
        
        col_missing, col_matched = st.columns(2)
        
        with col_missing:
            st.markdown("### ⚠️ Top Missing Skills")
            st.markdown("These skills are highly requested in top matches but missing from your resume:")
            missing_skills = gaps.get("top_missing", [])
            if not missing_skills:
                st.success("Great job! No major skill gaps identified in the top matches.")
            else:
                for skill, count in missing_skills[:10]:
                    st.markdown(
                        f'<div style="background:#ef444411;border:1px solid #ef444433;border-radius:8px;'
                        f'padding:8px 12px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">'
                        f'<span style="color:#fca5a5;font-weight:600;">{skill}</span>'
                        f'<span style="background:#ef444433;color:#fca5a5;padding:2px 8px;border-radius:99px;font-size:0.75rem;">'
                        f'Requested in {count} job(s)</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        
        with col_matched:
            st.markdown("### ✅ Top Matched Skills")
            st.markdown("These in-demand skills from your resume match the job requirements:")
            matched_skills = gaps.get("top_matched", [])
            if not matched_skills:
                st.info("No matching skills found in the top listings yet.")
            else:
                for skill, count in matched_skills[:10]:
                    st.markdown(
                        f'<div style="background:#22c55e11;border:1px solid #22c55e33;border-radius:8px;'
                        f'padding:8px 12px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">'
                        f'<span style="color:#86efac;font-weight:600;">{skill}</span>'
                        f'<span style="background:#22c55e33;color:#86efac;padding:2px 8px;border-radius:99px;font-size:0.75rem;">'
                        f'Requested in {count} job(s)</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        
        # Display Plotly Skill Gap charts
        st.markdown("<br>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.plotly_chart(matched_skills_chart(jobs_all), use_container_width=True)
        with col_c2:
            st.plotly_chart(skill_gap_chart(jobs_all), use_container_width=True)
            
        # Career Coach Report Section
        st.divider()
        st.markdown("### 🎓 AI Career Coach Report")
        
        if not st.session_state.gemini_key:
            st.warning("Please configure your Gemini API Key in the sidebar to generate the AI Career Coach report.")
        else:
            if not st.session_state.gap_report:
                if st.button("✨ Generate AI Career Coach Report", use_container_width=True):
                    with st.spinner("Gemini is analyzing your profile and the job market…"):
                        gaps_full = analyze_gaps(profile, jobs_all, gemini_api_key=st.session_state.gemini_key)
                        st.session_state.gap_report = gaps_full.get("gemini_report", "")
                    st.rerun()
            else:
                st.markdown(f'<div class="cover-letter-box">{st.session_state.gap_report}</div>',
                            unsafe_allow_html=True)
                
                # Download button for report
                st.download_button(
                    "⬇️ Download AI Career Report (.md)",
                    st.session_state.gap_report,
                    file_name="career_coach_report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                if st.button("🔄 Regenerate Report", use_container_width=True):
                    st.session_state.gap_report = ""
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – MY PROFILE
# ══════════════════════════════════════════════════════════════════════════════
with tab_profile:
    if not profile:
        st.info("Upload your resume and scan to see your profile.")
    else:
        section_header("👤", "Parsed Resume Profile", "Extracted from your uploaded resume")
        col_info, col_meta = st.columns([2, 1])

        with col_info:
            edu_html = "".join(
                f'<span style="background:#8b5cf622;color:#c4b5fd;border:1px solid #8b5cf655;'
                f'padding:4px 14px;border-radius:99px;font-size:0.8rem;font-weight:600;">{e}</span>'
                for e in profile.get("education", [])
            )
            summary_text = profile.get("summary", "")
            summary_html = (
                f'<div style="margin-top:14px;font-size:0.85rem;color:#94a3b8;line-height:1.6;">'
                f'{summary_text}</div>'
            ) if summary_text else ""

            st.markdown(
                f"""
<div style="background:linear-gradient(135deg,#1e1b4b,#1a1a2e);border:1px solid #2d2b55;
            border-radius:14px;padding:24px 28px;margin-bottom:20px;">
  <div style="font-size:1.4rem;font-weight:800;color:#e2e8f0;">{profile.get('name','Your Name')}</div>
  <div style="color:#94a3b8;margin-top:6px;">
    {"📧 " + profile.get('email','') if profile.get('email') else ""}
    {"&nbsp;|&nbsp; 📞 " + profile.get('phone','') if profile.get('phone') else ""}
  </div>
  <div style="margin-top:12px;padding-top:12px;border-top:1px solid #2d2b55;display:flex;flex-wrap:wrap;gap:6px;">
    <span style="background:#6366f122;color:#818cf8;border:1px solid #6366f155;
                 padding:4px 14px;border-radius:99px;font-size:0.8rem;font-weight:600;">
      {profile.get('experience_level','')}</span>
    <span style="background:#06b6d422;color:#22d3ee;border:1px solid #06b6d455;
                 padding:4px 14px;border-radius:99px;font-size:0.8rem;font-weight:600;">
      {profile.get('experience_years',0)} yrs experience</span>
    {edu_html}
  </div>
  {summary_html}
</div>
""", unsafe_allow_html=True)

            st.markdown("**🛠️ Detected Skills**")
            render_skill_pills(profile.get("skills", []), "#6366f1")

        with col_meta:
            st.markdown("**🎯 Target Job Titles**")
            for t in profile.get("job_titles", [])[:10]:
                st.markdown(
                    f'<div style="background:#1e1b4b;border:1px solid #2d2b55;border-radius:8px;'
                    f'padding:8px 12px;margin-bottom:6px;font-size:0.82rem;color:#c4c0e8;">'
                    f'🏷️ {t.title()}</div>',
                    unsafe_allow_html=True,
                )

        with st.expander("📄 Raw extracted text"):
            st.text_area("Text", profile.get("raw_text","")[:3000], height=250, disabled=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    if not jobs_all:
        st.info("Run a scan first.")
    else:
        section_header("📊", "Market Intelligence", "Insights from your job scan")

        cg, ch = st.columns([1, 2])
        with cg:
            try:
                st.plotly_chart(match_score_gauge(avg_score), use_container_width=True)
            except Exception as e:
                st.error(f"Gauge error: {e}")
        with ch:
            st.plotly_chart(match_score_histogram(jobs_all), use_container_width=True)

        cp, cc = st.columns(2)
        with cp:
            st.plotly_chart(source_pie_chart(jobs_all), use_container_width=True)
        with cc:
            st.plotly_chart(top_companies_chart(jobs_all), use_container_width=True)

        st.divider()
        st.markdown("### 💰 Salary Benchmarking & Market Intelligence")
        
        col_est, col_bench = st.columns(2)
        
        with col_est:
            est = estimate_market_salary(profile)
            if est:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg, #1e1b4b, #12103a);border:1px solid #8b5cf655;
                            border-top: 4px solid #8b5cf6;border-radius:12px;padding:20px;margin-bottom:15px;">
                  <div style="font-size:0.85rem;color:#a78bfa;font-weight:700;text-transform:uppercase;">Estimated Market Value (AU)</div>
                  <div style="font-size:1.8rem;font-weight:800;color:#e2e8f0;margin-top:4px;">
                    {est['currency']} ${est['median']:,} <span style="font-size:0.95rem;font-weight:400;color:#94a3b8;">/ year</span>
                  </div>
                  <div style="font-size:0.82rem;color:#94a3b8;margin-top:6px;line-height:1.4;">
                    Estimated benchmark for a <b>{est['role']}</b> role with <b>{est['years']} years</b> of experience in the AU market.
                  </div>
                  <div style="display:flex;justify-content:space-between;margin-top:12px;font-size:0.8rem;color:#c4c0e8;
                              border-top:1px solid #2d2b55;padding-top:8px;">
                    <span>📉 25th Pctl: <b>${est['low']:,}</b></span>
                    <span>📈 75th Pctl: <b>${est['high']:,}</b></span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Could not determine AU market rate estimation from resume profile titles.")
                
        with col_bench:
            bench = benchmark_from_listings(jobs_all)
            if bench.get("has_data"):
                overall = bench["overall"]
                st.markdown(f"""
                <div style="background:linear-gradient(135deg, #1e1b4b, #12103a);border:1px solid #06b6d455;
                            border-top: 4px solid #06b6d4;border-radius:12px;padding:20px;margin-bottom:15px;">
                  <div style="font-size:0.85rem;color:#67e8f9;font-weight:700;text-transform:uppercase;">Listing Salary Benchmarks</div>
                  <div style="font-size:1.8rem;font-weight:800;color:#e2e8f0;margin-top:4px;">
                    AUD ${int(overall['median']):,} <span style="font-size:0.95rem;font-weight:400;color:#94a3b8;">Median</span>
                  </div>
                  <div style="font-size:0.82rem;color:#94a3b8;margin-top:6px;line-height:1.4;">
                    Aggregated across <b>{bench['count']}</b> scanned job listings that published salary details.
                  </div>
                  <div style="display:flex;justify-content:space-between;margin-top:12px;font-size:0.8rem;color:#c4c0e8;
                              border-top:1px solid #2d2b55;padding-top:8px;">
                    <span>📉 Min: <b>${int(overall['min']):,}</b></span>
                    <span>📈 Max: <b>${int(overall['max']):,}</b></span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No listings with salary data found in this scan. Use Adzuna or other sources to see listing-based benchmarks.")
        
        sal_fig = salary_range_chart(jobs_all)
        if sal_fig:
            st.plotly_chart(sal_fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 – EXPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_export:
    section_header("📥", "Export Results", "Download your matches as PDF, CSV, or JSON")

    if not jobs_all:
        st.info("Run a scan first.")
    else:
        df_rows = []
        for j in jobs_all:
            status_key = st.session_state.job_statuses.get(j["id"], "none")
            icon, label, _ = JOB_STATUSES[status_key][:3]
            df_rows.append({
                "Match Score (%)":  j["match_score"],
                "Status":           f"{icon} {label}",
                "Job Title":        j["title"],
                "Company":          j["company"],
                "Location":         j["location"],
                "Remote":           "Yes" if j.get("is_remote") else "No",
                "Salary Min":       j.get("salary_min",""),
                "Salary Max":       j.get("salary_max",""),
                "Currency":         j.get("salary_currency",""),
                "Posted Date":      j.get("posted_date",""),
                "Source":           j.get("source",""),
                "Matched Skills":   ", ".join(j.get("matched_skills",[])),
                "Skill Gaps":       ", ".join(j.get("skill_gaps",[])),
                "Notes":            st.session_state.job_notes.get(j["id"],""),
                "URL":              j.get("url",""),
            })

        df = pd.DataFrame(df_rows)
        st.markdown("**Preview (top 20)**")
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)

        ec, ej, ep = st.columns(3)
        with ec:
            st.download_button(
                "⬇️  Download CSV", df.to_csv(index=False),
                "job_market_scan.csv", "text/csv", use_container_width=True,
            )
        with ej:
            st.download_button(
                "⬇️  Download JSON", _json.dumps(jobs_all, indent=2, default=str),
                "job_market_scan.json", "application/json", use_container_width=True,
            )
        with ep:
            with st.spinner("Generating PDF report…"):
                pdf_data = generate_pdf(jobs_all, profile, top_n=30)
            st.download_button(
                "⬇️  Download PDF Report", pdf_data,
                "job_market_scan.pdf", "application/pdf", use_container_width=True,
            )
        st.markdown(
            f'<div style="background:#1a1a2e;border:1px solid #2d2b55;border-radius:12px;'
            f'padding:16px 24px;margin-top:16px;font-size:0.85rem;color:#94a3b8;">'
            f'Total: <b>{len(df)}</b> jobs &nbsp;|&nbsp;'
            f'AU jobs: <b>{au_cnt}</b> &nbsp;|&nbsp;'
            f'Strong matches: <b>{len(df[df["Match Score (%)"] >= 70])}</b> &nbsp;|&nbsp;'
            f'Sources: <b>{", ".join(sorted(df["Source"].unique()))}</b></div>',
            unsafe_allow_html=True,
        )
