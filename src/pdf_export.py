"""
pdf_export.py - Generate a polished PDF of job scan results using reportlab.
Falls back to styled HTML if reportlab is unavailable.
"""

from __future__ import annotations

import io
from typing import Any
from datetime import datetime


def generate_pdf(
    jobs: list[dict[str, Any]],
    profile: dict[str, Any],
    top_n: int = 30,
) -> bytes:
    """
    Generate a PDF report of top job matches.
    Returns raw bytes ready for Streamlit download_button.
    """
    try:
        return _reportlab_pdf(jobs[:top_n], profile)
    except ImportError:
        return _html_fallback(jobs[:top_n], profile).encode("utf-8")


# ── ReportLab PDF ─────────────────────────────────────────────────────────────

def _reportlab_pdf(jobs: list[dict[str, Any]], profile: dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles   import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units    import cm
    from reportlab.lib           import colors
    from reportlab.platypus      import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    # Colours
    PURPLE = colors.HexColor("#6366f1")
    DARK   = colors.HexColor("#1e1b4b")
    SLATE  = colors.HexColor("#94a3b8")
    GREEN  = colors.HexColor("#22c55e")
    AMBER  = colors.HexColor("#f59e0b")
    RED    = colors.HexColor("#ef4444")
    WHITE  = colors.white
    LIGHT  = colors.HexColor("#f8fafc")

    styles = getSampleStyleSheet()

    def style(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    H1    = style("H1", fontSize=22, textColor=PURPLE, spaceAfter=4, fontName="Helvetica-Bold")
    H2    = style("H2", fontSize=13, textColor=DARK,   spaceAfter=4, fontName="Helvetica-Bold")
    BODY  = style("BODY", fontSize=9, textColor=colors.HexColor("#334155"), leading=13)
    SMALL = style("SMALL", fontSize=8, textColor=SLATE, leading=11)
    SKILL = style("SKILL", fontSize=8, textColor=colors.HexColor("#4f46e5"))
    META  = style("META", fontSize=8, textColor=SLATE)

    def score_colour(s: float):
        if s >= 70: return GREEN
        if s >= 45: return AMBER
        return RED

    story = []

    # ── Cover page ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("🔭 Job Market Scanner", H1))
    story.append(Paragraph(f"Results for <b>{profile.get('name', 'Candidate')}</b>", H2))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%d %B %Y, %H:%M')}  •  "
        f"Top {len(jobs)} matches shown", SMALL
    ))
    story.append(HRFlowable(width="100%", color=PURPLE, thickness=1, spaceAfter=12))

    # ── Profile summary ──────────────────────────────────────────────────────
    story.append(Paragraph("Candidate Summary", H2))
    profile_data = [
        ["Skills detected",   ", ".join(profile.get("skills", [])[:20]) or "—"],
        ["Experience",        f"{profile.get('experience_years',0)} years — {profile.get('experience_level','')}"],
        ["Education",         ", ".join(profile.get("education", [])) or "—"],
        ["Target Roles",      ", ".join(profile.get("job_titles", [])[:5]) or "—"],
        ["Email",             profile.get("email", "—")],
    ]
    tbl = Table(profile_data, colWidths=[4*cm, 13*cm])
    tbl.setStyle(TableStyle([
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("TEXTCOLOR",  (0,0), (0,-1), PURPLE),
        ("TEXTCOLOR",  (1,0), (1,-1), colors.HexColor("#334155")),
        ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT, WHITE]),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("GRID",       (0,0), (-1,-1), 0.25, colors.HexColor("#e2e8f0")),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.6*cm))

    # ── Job listings ─────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", color=PURPLE, thickness=1, spaceAfter=8))
    story.append(Paragraph(f"Top {len(jobs)} Job Matches", H2))
    story.append(Spacer(1, 0.3*cm))

    for rank, job in enumerate(jobs, 1):
        sc       = job.get("match_score", 0)
        sc_col   = score_colour(sc)
        sal      = ""
        if job.get("salary_min") or job.get("salary_max"):
            cur = job.get("salary_currency", "AUD")
            mn  = job.get("salary_min")
            mx  = job.get("salary_max")
            if mn and mx and mn != mx:
                sal = f" | 💰 {cur} ${mn:,.0f}–${mx:,.0f}"
            elif mx:
                sal = f" | 💰 Up to {cur} ${mx:,.0f}"

        matched = ", ".join(job.get("matched_skills", [])[:8]) or "—"
        gaps    = ", ".join(job.get("skill_gaps",    [])[:6]) or "—"

        block = [
            Table(
                [[
                    Paragraph(f"#{rank}  {job.get('title','N/A')}", style(
                        f"T{rank}", fontSize=11, textColor=DARK, fontName="Helvetica-Bold")),
                    Paragraph(f"{sc:.0f}%", style(
                        f"S{rank}", fontSize=14, textColor=sc_col,
                        fontName="Helvetica-Bold", alignment=2)),
                ]],
                colWidths=[13*cm, 4*cm],
            ),
            Paragraph(
                f"🏢 {job.get('company','—')}  |  📍 {job.get('location','—')}  |  "
                f"{job.get('source','')}  |  📅 {job.get('posted_date','N/A')}{sal}", SMALL
            ),
            Paragraph(
                (job.get("description","") or "")[:350] + ("…" if len(job.get("description","") or "") > 350 else ""),
                BODY
            ),
            Paragraph(f"<b>✅ Matched:</b> {matched}", SKILL),
            Paragraph(f"<b>⚠️ Gaps:</b> {gaps}", style(f"G{rank}", fontSize=8, textColor=AMBER)),
            Paragraph(
                f"<link href=\"{job.get('url','')}\">🔗 Apply: {job.get('url','')[:80]}</link>",
                style(f"L{rank}", fontSize=8, textColor=PURPLE)
            ),
        ]

        inner_tbl = Table([[b] for b in block], colWidths=[17*cm])
        inner_tbl.setStyle(TableStyle([
            ("BOX",          (0,0), (-1,-1), 0.5, colors.HexColor("#2d2b55")),
            ("LEFTPADDING",  (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING",   (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[LIGHT, WHITE, WHITE, LIGHT, WHITE, WHITE]),
        ]))
        story.append(KeepTogether([inner_tbl, Spacer(1, 0.3*cm)]))

    doc.build(story)
    return buf.getvalue()


# ── HTML fallback ─────────────────────────────────────────────────────────────

def _html_fallback(jobs: list[dict[str, Any]], profile: dict[str, Any]) -> str:
    def sc_col(s):
        return "#22c55e" if s >= 70 else "#f59e0b" if s >= 45 else "#ef4444"

    rows = "".join(
        f"""<div style="border:1px solid #2d2b55;border-left:4px solid {sc_col(j['match_score'])};
            border-radius:8px;padding:16px;margin-bottom:12px;background:#1e1b4b;">
          <div style="display:flex;justify-content:space-between;">
            <b style="color:#e2e8f0;font-size:14px;">#{i+1}. {j.get('title','')}</b>
            <b style="color:{sc_col(j['match_score'])};font-size:18px;">{j['match_score']:.0f}%</b>
          </div>
          <div style="color:#94a3b8;font-size:11px;margin:4px 0;">
            🏢 {j.get('company','')} | 📍 {j.get('location','')} | {j.get('source','')}
          </div>
          <div style="color:#94a3b8;font-size:11px;">{(j.get('description','') or '')[:250]}…</div>
          <a href="{j.get('url','')}" style="color:#6366f1;font-size:11px;">Apply →</a>
        </div>"""
        for i, j in enumerate(jobs)
    )

    return f"""<!DOCTYPE html><html><head>
<meta charset="utf-8">
<title>Job Market Scanner — Results</title>
<style>
  body{{background:#0f0c29;color:#e2e8f0;font-family:Inter,sans-serif;padding:32px;max-width:900px;margin:0 auto;}}
  h1{{color:#6366f1;}} h2{{color:#94a3b8;font-size:14px;}}
  @media print{{body{{background:white;color:black;}}}}
</style></head><body>
<h1>🔭 Job Market Scanner — Results</h1>
<h2>Candidate: {profile.get('name','')} | Generated {datetime.now().strftime('%d %B %Y %H:%M')}</h2>
<hr style="border-color:#2d2b55;">
{rows}
</body></html>"""
