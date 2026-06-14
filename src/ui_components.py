"""
ui_components.py - Reusable Streamlit UI building blocks with custom styling.
"""

from __future__ import annotations
from typing import Any
import streamlit as st


# ── Score badge colours ────────────────────────────────────────────────────────

def _score_colour(score: float) -> str:
    if score >= 70:
        return "#22c55e"   # green
    elif score >= 45:
        return "#f59e0b"   # amber
    else:
        return "#ef4444"   # red


def _score_label(score: float) -> str:
    if score >= 70:
        return "Strong Match"
    elif score >= 45:
        return "Potential Match"
    else:
        return "Low Match"


# ── Skill pills ────────────────────────────────────────────────────────────────

def skill_pill(skill: str, colour: str = "#6366f1") -> str:
    """Return HTML for a skill badge."""
    return (
        f'<span style="background:{colour}22;color:{colour};border:1px solid {colour}55;'
        f'border-radius:999px;padding:3px 10px;font-size:0.75rem;font-weight:600;'
        f'margin:2px;display:inline-block;">{skill}</span>'
    )


def render_skill_pills(skills: list[str], colour: str = "#6366f1") -> None:
    if not skills:
        st.caption("None detected")
        return
    st.markdown(
        " ".join(skill_pill(s, colour) for s in skills),
        unsafe_allow_html=True,
    )


# ── Job card ──────────────────────────────────────────────────────────────────

def render_job_card(job: dict[str, Any], idx: int) -> None:
    score     = job.get("match_score", 0)
    colour    = _score_colour(score)
    label     = _score_label(score)
    matched   = job.get("matched_skills", [])
    gaps      = job.get("skill_gaps", [])
    salary    = _format_salary(job)
    remote_tag = "🌐 Remote" if job.get("is_remote") else f"📍 {job.get('location','')}"

    with st.container():
        st.markdown(
            f"""
<div style="
    background:linear-gradient(135deg,#1e1b4b 0%,#1a1a2e 100%);
    border:1px solid #2d2b55;
    border-left:4px solid {colour};
    border-radius:12px;
    padding:20px 24px;
    margin-bottom:14px;
    position:relative;
">
  <!-- Header row -->
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
    <div>
      <div style="font-size:1.05rem;font-weight:700;color:#e2e8f0;margin-bottom:2px;">{job.get('title','N/A')}</div>
      <div style="font-size:0.88rem;color:#94a3b8;">
        🏢 {job.get('company','Unknown')} &nbsp;|&nbsp; {remote_tag} &nbsp;|&nbsp; 📅 {job.get('posted_date','') or 'N/A'}
      </div>
      {f'<div style="font-size:0.82rem;color:#64748b;margin-top:4px;">💰 {salary}</div>' if salary else ''}
    </div>
    <div style="text-align:right;min-width:100px;">
      <div style="font-size:1.6rem;font-weight:800;color:{colour};line-height:1;">{score:.0f}%</div>
      <div style="font-size:0.72rem;font-weight:600;color:{colour};background:{colour}22;
                  padding:2px 8px;border-radius:99px;margin-top:2px;">{label}</div>
      <div style="font-size:0.7rem;color:#64748b;margin-top:3px;">via {job.get('source','')}</div>
    </div>
  </div>
  <!-- Description snippet -->
  <div style="font-size:0.82rem;color:#94a3b8;margin-top:10px;line-height:1.5;
              border-top:1px solid #2d2b55;padding-top:10px;">
    {(job.get('description','')[:220] + '…') if job.get('description') else ''}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        # Expandable details
        with st.expander("🔍 View details & skills", expanded=False):
            col_m, col_g = st.columns(2)
            with col_m:
                st.markdown("**✅ Matched Skills**")
                render_skill_pills(matched[:20], "#22c55e")
            with col_g:
                st.markdown("**⚠️ Skill Gaps**")
                render_skill_pills(gaps[:15], "#f59e0b")

            st.markdown(
                f'<a href="{job.get("url","#")}" target="_blank" '
                f'style="display:inline-block;margin-top:12px;padding:8px 20px;'
                f'background:linear-gradient(90deg,#6366f1,#8b5cf6);color:white;'
                f'border-radius:8px;text-decoration:none;font-weight:600;font-size:0.85rem;">'
                f'🚀 Apply Now</a>',
                unsafe_allow_html=True,
            )


def _format_salary(job: dict[str, Any]) -> str:
    mn = job.get("salary_min")
    mx = job.get("salary_max")
    cur = job.get("salary_currency", "AUD")
    if mn and mx:
        return f"{cur} ${mn:,.0f} – ${mx:,.0f}"
    elif mx:
        return f"Up to {cur} ${mx:,.0f}"
    elif mn:
        return f"From {cur} ${mn:,.0f}"
    return ""


# ── Metric cards ──────────────────────────────────────────────────────────────

def metric_card(label: str, value: str, sub: str = "", colour: str = "#6366f1") -> str:
    return f"""
<div style="
    background:linear-gradient(135deg,#1e1b4b,#1a1a2e);
    border:1px solid #2d2b55;
    border-top:3px solid {colour};
    border-radius:12px;
    padding:18px 22px;
    text-align:center;
">
  <div style="font-size:2rem;font-weight:800;color:{colour};">{value}</div>
  <div style="font-size:0.88rem;font-weight:600;color:#e2e8f0;margin-top:4px;">{label}</div>
  {f'<div style="font-size:0.75rem;color:#64748b;margin-top:2px;">{sub}</div>' if sub else ''}
</div>"""


def render_metrics_row(metrics: list[tuple[str, str, str, str]]) -> None:
    """metrics: list of (label, value, subtitle, colour)"""
    cols = st.columns(len(metrics))
    for col, (label, value, sub, colour) in zip(cols, metrics):
        with col:
            st.markdown(metric_card(label, value, sub, colour), unsafe_allow_html=True)


# ── Section header ────────────────────────────────────────────────────────────

def section_header(icon: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
<div style="margin:24px 0 16px 0;">
  <div style="font-size:1.4rem;font-weight:700;color:#e2e8f0;">{icon} {title}</div>
  {f'<div style="font-size:0.85rem;color:#64748b;">{subtitle}</div>' if subtitle else ''}
</div>
""",
        unsafe_allow_html=True,
    )
