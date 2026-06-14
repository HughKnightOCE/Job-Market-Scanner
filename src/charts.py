"""
charts.py - Plotly chart builders for the analytics tab.
"""

from __future__ import annotations
from collections import Counter
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st


_BG     = "rgba(0,0,0,0)"   # transparent
_PAPER  = "rgba(0,0,0,0)"
_GRID   = "#1e293b"
_TEXT   = "#94a3b8"
_PURPLE = "#6366f1"
_CYAN   = "#06b6d4"
_AMBER  = "#f59e0b"
_GREEN  = "#22c55e"
_RED    = "#ef4444"

_LAYOUT = dict(
    paper_bgcolor=_PAPER,
    plot_bgcolor=_BG,
    font=dict(color=_TEXT, family="Inter, sans-serif"),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#2d2b55"),
)


def match_score_histogram(jobs: list[dict[str, Any]]) -> go.Figure:
    """Distribution of match scores."""
    scores = [j["match_score"] for j in jobs]
    fig = go.Figure(go.Histogram(
        x=scores,
        nbinsx=20,
        marker=dict(
            color=scores,
            colorscale=[[0, _RED], [0.45, _AMBER], [1, _GREEN]],
            line=dict(width=0),
        ),
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Match Score Distribution", font=dict(size=14, color="#e2e8f0")),
        xaxis=dict(title="Match Score (%)", gridcolor=_GRID, zeroline=False),
        yaxis=dict(title="Number of Jobs", gridcolor=_GRID),
    )
    return fig


def salary_range_chart(jobs: list[dict[str, Any]]) -> go.Figure | None:
    """Box / strip chart for salary ranges."""
    salary_jobs = [j for j in jobs if j.get("salary_min") or j.get("salary_max")]
    if not salary_jobs:
        return None

    df = pd.DataFrame({
        "title":   [j["title"][:35] for j in salary_jobs],
        "min":     [j.get("salary_min") or j.get("salary_max") for j in salary_jobs],
        "max":     [j.get("salary_max") or j.get("salary_min") for j in salary_jobs],
        "score":   [j["match_score"] for j in salary_jobs],
    })

    fig = go.Figure()
    fig.add_trace(go.Box(
        y=df["max"],
        name="Salary Max",
        marker_color=_PURPLE,
        boxmean=True,
    ))
    fig.add_trace(go.Box(
        y=df["min"],
        name="Salary Min",
        marker_color=_CYAN,
        boxmean=True,
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Salary Range Overview", font=dict(size=14, color="#e2e8f0")),
        yaxis=dict(title="Annual Salary", gridcolor=_GRID),
    )
    return fig


def top_companies_chart(jobs: list[dict[str, Any]]) -> go.Figure:
    """Bar chart of top hiring companies."""
    companies = [j["company"] for j in jobs if j.get("company")]
    counts = Counter(companies).most_common(15)
    if not counts:
        names, vals = ["No data"], [1]
    else:
        names, vals = zip(*counts)

    fig = go.Figure(go.Bar(
        x=list(vals),
        y=list(names),
        orientation="h",
        marker=dict(
            color=list(vals),
            colorscale=[[0, "#3730a3"], [1, _PURPLE]],
        ),
        text=list(vals),
        textposition="inside",
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Top Hiring Companies", font=dict(size=14, color="#e2e8f0")),
        xaxis=dict(title="Job Openings", gridcolor=_GRID),
        yaxis=dict(autorange="reversed"),
        height=max(300, len(names) * 28),
    )
    return fig


def source_pie_chart(jobs: list[dict[str, Any]]) -> go.Figure:
    """Donut chart showing job source breakdown."""
    sources = Counter(j.get("source", "Unknown") for j in jobs)
    labels  = list(sources.keys())
    values  = list(sources.values())

    colours = [
        _PURPLE, _CYAN, _AMBER, _GREEN, _RED,
        "#ec4899", "#14b8a6", "#f97316", "#a855f7", "#3b82f6",
    ]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colours[:len(labels)], line=dict(color="#1a1a2e", width=2)),
        textfont=dict(size=12),
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Jobs by Source", font=dict(size=14, color="#e2e8f0")),
    )
    return fig


def skill_gap_chart(jobs: list[dict[str, Any]], top_n: int = 20) -> go.Figure:
    """Horizontal bar of most common skill gaps across all top jobs."""
    all_gaps: list[str] = []
    for job in jobs[:50]:   # only consider top 50 jobs
        all_gaps.extend(job.get("skill_gaps", []))

    counts = Counter(all_gaps).most_common(top_n)
    if not counts:
        skills, vals = ["No gaps found"], [1]
    else:
        skills, vals = zip(*counts)

    fig = go.Figure(go.Bar(
        x=list(vals),
        y=list(skills),
        orientation="h",
        marker=dict(color=_AMBER),
        text=list(vals),
        textposition="inside",
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Top Skill Gaps (Skills to Learn)", font=dict(size=14, color="#e2e8f0")),
        xaxis=dict(title="Frequency in Job Listings", gridcolor=_GRID),
        yaxis=dict(autorange="reversed"),
        height=max(300, len(skills) * 28),
    )
    return fig


def matched_skills_chart(jobs: list[dict[str, Any]], top_n: int = 20) -> go.Figure:
    """Bar chart of most frequently matched skills."""
    all_matched: list[str] = []
    for job in jobs[:50]:
        all_matched.extend(job.get("matched_skills", []))

    counts = Counter(all_matched).most_common(top_n)
    if not counts:
        skills, vals = ["No matches"], [1]
    else:
        skills, vals = zip(*counts)

    fig = go.Figure(go.Bar(
        x=list(vals),
        y=list(skills),
        orientation="h",
        marker=dict(color=_GREEN),
        text=list(vals),
        textposition="inside",
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Your Top Matched Skills", font=dict(size=14, color="#e2e8f0")),
        xaxis=dict(title="Frequency in Job Listings", gridcolor=_GRID),
        yaxis=dict(autorange="reversed"),
        height=max(300, len(skills) * 28),
    )
    return fig


def match_score_gauge(score: float) -> go.Figure:
    """Gauge chart for average match score."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(suffix="%", font=dict(size=40, color="#e2e8f0")),
        gauge=dict(
            axis=dict(range=[0, 100], tickfont=dict(color=_TEXT)),
            bar=dict(color=_PURPLE),
            bgcolor="rgba(30,27,75,0.5)",
            bordercolor="#2d2b55",
            steps=[
                dict(range=[0, 45],  color="#ef444422"),
                dict(range=[45, 70], color="#f59e0b22"),
                dict(range=[70, 100], color="#22c55e22"),
            ],
            threshold=dict(
                line=dict(color=_GREEN, width=3),
                thickness=0.8,
                value=70,
            ),
        ),
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Average Match Score", font=dict(size=14, color="#e2e8f0")),
        height=220,
    )
    return fig
