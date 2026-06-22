"""
ui_components.py - Reusable Streamlit UI building blocks.
"""

from __future__ import annotations
from typing import Any
import streamlit as st
from src.config import JOB_STATUSES


def _score_colour(score: float) -> str:
    if score >= 70: return "#22c55e"
    if score >= 45: return "#f59e0b"
    return "#ef4444"


def _score_label(score: float) -> str:
    if score >= 70: return "Strong Match"
    if score >= 45: return "Potential Match"
    return "Low Match"


def skill_pill(skill: str, colour: str = "#6366f1") -> str:
    return (
        f'<span style="background:{colour}22;color:{colour};border:1px solid {colour}55;'
        f'border-radius:999px;padding:3px 10px;font-size:0.75rem;font-weight:600;'
        f'margin:2px;display:inline-block;">{skill}</span>'
    )


def render_skill_pills(skills: list[str], colour: str = "#6366f1") -> None:
    if not skills:
        st.caption("None detected")
        return
    st.markdown(" ".join(skill_pill(s, colour) for s in skills), unsafe_allow_html=True)


def _source_flag(source: str) -> str:
    """Return a flag/emoji for the job source."""
    flags = {
        "Seek": "🔵", "Jora": "🟣", "Indeed": "🔴",
        "GradConnection": "🎓", "Adzuna": "🟠",
        "EthicalJobs": "🌱",
    }
    return flags.get(source, "🌐")


def _format_salary(job: dict) -> str:
    mn, mx = job.get("salary_min"), job.get("salary_max")
    cur    = job.get("salary_currency","AUD")
    if mn and mx and mn != mx: return f"{cur} ${mn:,.0f} – ${mx:,.0f}"
    if mx:  return f"Up to {cur} ${mx:,.0f}"
    if mn:  return f"From {cur} ${mn:,.0f}"
    return ""


def render_job_card(job: dict[str, Any], idx: int, session_state=None) -> None:
    score    = job.get("match_score", 0)
    colour   = _score_colour(score)
    label    = _score_label(score)
    matched  = job.get("matched_skills", [])
    gaps     = job.get("skill_gaps", [])
    salary   = _format_salary(job)
    source   = job.get("source","")
    flag     = _source_flag(source)
    loc_icon = "🌐" if job.get("is_remote") else "📍"
    loc_text = job.get("location","")
    jid      = job.get("id","")

    # Current tracked status
    status_key = "none"
    if session_state is not None:
        status_key = session_state.job_statuses.get(jid, "none")
    s_icon, s_label, s_colour = JOB_STATUSES[status_key][:3]

    with st.container():
        st.markdown(
            f"""
<div style="
  background:linear-gradient(135deg,#1e1b4b 0%,#1a1a2e 100%);
  border:1px solid #2d2b55;
  border-left:4px solid {colour};
  border-radius:12px;
  padding:18px 22px;
  margin-bottom:12px;
">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
    <div style="flex:1;min-width:0;">
      <div style="font-size:1.05rem;font-weight:700;color:#e2e8f0;margin-bottom:3px;">{job.get('title','N/A')}</div>
      <div style="font-size:0.85rem;color:#94a3b8;">
        🏢 {job.get('company','Unknown')} &nbsp;|&nbsp;
        {loc_icon} {loc_text} &nbsp;|&nbsp;
        {flag} {source} &nbsp;|&nbsp;
        📅 {job.get('posted_date','') or 'N/A'}
      </div>
      {f'<div style="font-size:0.8rem;color:#64748b;margin-top:3px;">💰 {salary}</div>' if salary else ''}
      {f'<div style="margin-top:4px;"><span style="background:{s_colour}22;color:{s_colour};border:1px solid {s_colour}55;padding:2px 9px;border-radius:99px;font-size:0.7rem;font-weight:700;">{s_icon} {s_label}</span></div>' if status_key != 'none' else ''}
    </div>
    <div style="text-align:right;min-width:90px;">
      <div style="font-size:1.6rem;font-weight:800;color:{colour};line-height:1;">{score:.0f}%</div>
      <div style="font-size:0.7rem;font-weight:600;color:{colour};background:{colour}22;
                  padding:2px 8px;border-radius:99px;margin-top:2px;">{label}</div>
    </div>
  </div>
  <div style="font-size:0.81rem;color:#94a3b8;margin-top:10px;line-height:1.5;
              border-top:1px solid #2d2b55;padding-top:8px;">
    {(job.get('description','')[:240] + '…') if job.get('description') else '<i>No description available</i>'}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        with st.expander(f"🔍 Details, skills & tracker — {job.get('title','')[:40]}", expanded=False):
            # Skills
            col_m, col_g = st.columns(2)
            with col_m:
                st.markdown("**✅ Matched Skills**")
                render_skill_pills(matched[:20], "#22c55e")
            with col_g:
                st.markdown("**⚠️ Skill Gaps**")
                render_skill_pills(gaps[:15], "#f59e0b")

            st.markdown("---")

            # Status + notes tracker (inline in job card)
            if session_state is not None:
                tr1, tr2 = st.columns([1, 2])
                with tr1:
                    new_status = st.selectbox(
                        "Track status",
                        list(JOB_STATUSES.keys()),
                        index=list(JOB_STATUSES.keys()).index(status_key),
                        format_func=lambda k: f"{JOB_STATUSES[k][0]} {JOB_STATUSES[k][1]}",
                        key=f"status_{jid}_{idx}",
                    )
                    if new_status != status_key:
                        session_state.job_statuses[jid] = new_status
                        job["status"] = new_status
                        st.rerun()
                with tr2:
                    note = st.text_input(
                        "Notes",
                        value=session_state.job_notes.get(jid, ""),
                        placeholder="Interview date, contact, notes…",
                        key=f"note_{jid}_{idx}",
                    )
                    session_state.job_notes[jid] = note

            # Apply button
            st.markdown(
                f'<a href="{job.get("url","#")}" target="_blank" '
                f'style="display:inline-block;margin-top:10px;padding:9px 22px;'
                f'background:linear-gradient(90deg,#6366f1,#8b5cf6);color:white;'
                f'border-radius:8px;text-decoration:none;font-weight:700;font-size:0.85rem;">'
                f'🚀 Apply Now</a>',
                unsafe_allow_html=True,
            )


def metric_card(label: str, value: str, sub: str = "", colour: str = "#6366f1") -> str:
    return (
        f'<div style="background:linear-gradient(135deg,#1e1b4b,#1a1a2e);'
        f'border:1px solid #2d2b55;border-top:3px solid {colour};border-radius:12px;'
        f'padding:18px 22px;text-align:center;">'
        f'<div style="font-size:2rem;font-weight:800;color:{colour};">{value}</div>'
        f'<div style="font-size:0.88rem;font-weight:600;color:#e2e8f0;margin-top:4px;">{label}</div>'
        f'{"<div style=font-size:0.75rem;color:#64748b;margin-top:2px;>" + sub + "</div>" if sub else ""}'
        f'</div>'
    )


def render_metrics_row(metrics: list[tuple[str, str, str, str]]) -> None:
    cols = st.columns(len(metrics))
    for col, (label, value, sub, colour) in zip(cols, metrics):
        with col:
            st.markdown(metric_card(label, value, sub, colour), unsafe_allow_html=True)


def section_header(icon: str, title: str, subtitle: str = "") -> None:
    sub_html = f'<div style="font-size:0.85rem;color:#64748b;">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="margin:24px 0 16px 0;">'
        f'<div style="font-size:1.4rem;font-weight:700;color:#e2e8f0;">{icon} {title}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )
