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

    if scan_clicked:
        if not uploaded:
            st.error("Please upload your resume first!")
        elif not any([inc_seek, inc_jora, inc_indeed, inc_remote, inc_adzuna, inc_grad]):
            st.error("Select at least one job source!")
        else:
            st.session_state.last_location = location
            st.session_state.last_country  = country

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

            st.session_state.jobs      = scored
            st.session_state.scan_done = True
            st.rerun()

    if st.session_state.scan_done:
        n = len(st.session_state.jobs)
        f = len([j for j in st.session_state.jobs if j["match_score"] >= min_score])
        st.success(f"{n} jobs found  •  {f} above {min_score}%")

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

tab_jobs, tab_tracker, tab_cover, tab_profile, tab_analytics, tab_export = st.tabs([
    "🎯  Job Listings",
    "📋  Application Tracker",
    "💌  Cover Letter",
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

        cm, cg2 = st.columns(2)
        with cm:
            st.plotly_chart(matched_skills_chart(jobs_all), use_container_width=True)
        with cg2:
            st.plotly_chart(skill_gap_chart(jobs_all), use_container_width=True)

        sal_fig = salary_range_chart(jobs_all)
        if sal_fig:
            st.plotly_chart(sal_fig, use_container_width=True)
        else:
            st.info("No salary data available. Add an Adzuna API key for salary benchmarking.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 – EXPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_export:
    section_header("📥", "Export Results", "Download your matches as CSV or JSON")

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

        ec, ej = st.columns(2)
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
        st.markdown(
            f'<div style="background:#1a1a2e;border:1px solid #2d2b55;border-radius:12px;'
            f'padding:16px 24px;margin-top:16px;font-size:0.85rem;color:#94a3b8;">'
            f'Total: <b>{len(df)}</b> jobs &nbsp;|&nbsp;'
            f'AU jobs: <b>{au_cnt}</b> &nbsp;|&nbsp;'
            f'Strong matches: <b>{len(df[df["Match Score (%)"] >= 70])}</b> &nbsp;|&nbsp;'
            f'Sources: <b>{", ".join(sorted(df["Source"].unique()))}</b></div>',
            unsafe_allow_html=True,
        )
