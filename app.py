from __future__ import annotations

import os
import re
import html
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from store import load_sops, add_sop, delete_sop, get_portfolio_metrics
from grader import grade_sop, grade_sop_manual
from usage_scanner import scan_claude_code_logs, compute_actuals
from team import ROSTER, TEAM_NAMES, LOCATIONS, load_usage_logs, log_usage, delete_usage_log, get_team_metrics
from sheet_reader import fetch_all_remote_usage, fetch_sop_submissions, SOP_FORM_URL

GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScd6SMZOD-UPYY3qHtv-5KJOSooPQsstpJnuxMacv6DAxymqA/viewform"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1m-o1j571k60W5lJeUtGhhhZqdtHOCrdQN1csVeRlCK0/edit"


def load_all_sops() -> list[dict]:
    """Merge local SOPs with form-submitted SOPs, deduplicating by name."""
    local = load_sops()
    remote = fetch_sop_submissions()
    local_names = {s["name"].lower() for s in local}
    for r in remote:
        if r["name"].lower() not in local_names:
            local.append(r)
            local_names.add(r["name"].lower())
    return local


def clean_pasted_text(raw: str) -> str:
    """Strip HTML tags and decode entities from content pasted out of Google Docs / web pages."""
    text = html.unescape(raw)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(p|div|li|tr|td|th|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

st.set_page_config(
    page_title="EPM AI Leaderboard",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

DOORDASH_RED = "#FF3008"
DOORDASH_RED_SHADE = "#B71000"
DOORDASH_DARK = "#191919"
CARD_BG = "#1C1C1C"
CARD_BORDER = "#2E2E2E"
FLUSH = "#FA7463"
FLUSH_LIGHT = "#F9BEAA"
TIDE_POOL = "#00838A"
TIDE_POOL_LIGHT = "#17A3A9"
FOREST = "#004C1B"
SAGE = "#87B396"
LEMON = "#F0D73A"
CARAMEL = "#BD8800"
SKY = "#C5E8E9"
STONE = "#C7C6B7"
ACCENT_GREEN = SAGE
ACCENT_YELLOW = LEMON
ACCENT_BLUE = TIDE_POOL_LIGHT
TEXT_WHITE = "#FAFAFA"
TEXT_MUTED = "#9B9B9B"

LOGO_PATH = os.path.join(os.path.dirname(__file__), "dd_logo_full.png")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="st-"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .block-container { padding-top: 1.5rem; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #191919;
        border-right: 1px solid #2E2E2E;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdown"] h1 { color: #FAFAFA; }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #1C1C1C;
        border: 1px solid #2E2E2E;
        border-radius: 12px;
        padding: 20px 24px;
        border-top: 3px solid #FF3008;
    }
    div[data-testid="stMetric"] label { font-size: 0.8rem; color: #9B9B9B; font-weight: 500; letter-spacing: 0.02em; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 800; color: #FAFAFA; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 2px solid #2E2E2E; }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #9B9B9B;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: transparent;
        color: #FF3008;
        border-bottom: 3px solid #FF3008;
        font-weight: 700;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        background: #1C1C1C;
        border: 1px solid #2E2E2E;
        border-radius: 12px;
        border-left: 4px solid #FF3008;
    }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #FF3008 0%, #EB1700 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 24px;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #EB1700 0%, #CC1400 100%);
    }

    /* Dividers */
    hr { border-color: #2E2E2E; }

    /* Header styling */
    h1 { font-weight: 800; letter-spacing: -0.02em; }
    h3 { font-weight: 700; color: #FAFAFA; }

    /* Hide Streamlit chrome */
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    header[data-testid="stHeader"] { visibility: hidden !important; height: 0 !important; }
    [data-testid="stToolbar"] { visibility: hidden !important; }
    [data-testid="stDecoration"] { visibility: hidden !important; }
    [data-testid="stStatusWidget"] { visibility: hidden !important; }
    .stDeployButton { visibility: hidden !important; }
    /* Hide sidebar collapse arrow */
    button[data-testid="stBaseButton-headerNoPadding"] { display: none !important; }
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] button[kind="headerNoPadding"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


def grade_color(score: float) -> str:
    if score >= 8:
        return TIDE_POOL_LIGHT
    if score >= 6:
        return LEMON
    return DOORDASH_RED


def render_grade_badge(score: float, label: str = ""):
    color = grade_color(score)
    st.markdown(
        f'<div style="text-align:center">'
        f'<span style="font-size:2.2rem;font-weight:800;color:{color}">{score}</span>'
        f'<span style="color:{TEXT_MUTED};font-size:0.8rem">/10</span><br>'
        f'<span style="color:{TEXT_MUTED};font-size:0.8rem">{label}</span></div>',
        unsafe_allow_html=True,
    )


def render_radar_chart(scores: dict, title: str = ""):
    categories = list(scores.keys())
    values = list(scores.values())
    categories.append(categories[0])
    values.append(values[0])

    labels = [c.replace("_", " ").title() for c in categories]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=labels, fill="toself",
        fillcolor="rgba(0, 131, 138, 0.2)",
        line=dict(color=TIDE_POOL, width=2),
        marker=dict(size=6, color=TIDE_POOL_LIGHT),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 10], showticklabels=True, tickfont=dict(size=10, color=TEXT_MUTED), gridcolor="#2E2E2E"),
            angularaxis=dict(tickfont=dict(size=11, color=TEXT_WHITE), gridcolor="#2E2E2E"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=60, t=40, b=40),
        height=350,
        title=dict(text=title, font=dict(size=14, color=TEXT_WHITE)),
        showlegend=False,
    )
    return fig


def render_value_waterfall(sops: list[dict]):
    sorted_sops = sorted(sops, key=lambda s: s["annual_team_savings_hrs"], reverse=True)
    labels = []
    for s in sorted_sops:
        builder = s.get("built_by", "")
        labels.append(f"{s['name']}  ({builder})" if builder else s["name"])
    values = [s["annual_team_savings_hrs"] for s in sorted_sops]

    fig = go.Figure(go.Bar(
        x=list(values), y=labels, orientation="h",
        marker=dict(
            color=list(values),
            colorscale=[[0, TIDE_POOL], [0.5, FLUSH], [1, DOORDASH_RED]],
        ),
        text=[f"{v:,.0f} hrs" for v in values],
        textposition="outside",
        textfont=dict(color=TEXT_WHITE, size=12),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text="Annual Hours Recovered", font=dict(color=TEXT_MUTED)), tickfont=dict(color=TEXT_MUTED), gridcolor="#2E2E2E"),
        yaxis=dict(tickfont=dict(color=TEXT_WHITE, size=12), autorange="reversed"),
        margin=dict(l=10, r=80, t=20, b=40),
        height=max(250, len(labels) * 50 + 80),
    )
    return fig


def render_portfolio_scatter(sops: list[dict]):
    if not sops:
        return go.Figure()

    sorted_sops = sorted(sops, key=lambda s: s["annual_team_savings_hrs"], reverse=True)
    max_hrs = max(s["annual_team_savings_hrs"] for s in sorted_sops)

    fig = go.Figure()
    for s in sorted_sops:
        builder = s.get("built_by", "")
        fig.add_trace(go.Scatter(
            x=[s["overall_grade"]],
            y=[s["annual_team_savings_hrs"]],
            mode="markers",
            marker=dict(
                size=28,
                color=FLUSH,
                opacity=0.85,
                line=dict(width=2, color=DOORDASH_RED),
            ),
            name=s["name"],
            showlegend=False,
            hovertemplate=(
                f"<b>{s['name']}</b>"
                f"{'<br>Built by ' + builder if builder else ''}"
                f"<br>Grade: {s['overall_grade']}/10"
                f"<br>Annual hrs: {s['annual_team_savings_hrs']:,.0f}"
                f"<br>Team: {s['team_size']} people"
                f"<extra></extra>"
            ),
        ))

        short_name = s["name"].split("—")[0].strip()
        if len(short_name) > 20:
            words = short_name.split()
            mid = len(words) // 2
            short_name = " ".join(words[:mid]) + "<br>" + " ".join(words[mid:])

        label = f"<b>{short_name}</b><br>{builder}" if builder else f"<b>{short_name}</b>"

        fig.add_annotation(
            x=s["overall_grade"],
            y=s["annual_team_savings_hrs"],
            text=label,
            showarrow=True,
            arrowhead=0,
            arrowwidth=1,
            arrowcolor="#4A4A4A",
            ax=60,
            ay=-40,
            font=dict(color=TEXT_WHITE, size=10),
            align="left",
            bgcolor="rgba(28,28,28,0.85)",
            bordercolor="#2E2E2E",
            borderwidth=1,
            borderpad=6,
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title=dict(text="SOP Quality Score", font=dict(color=TEXT_MUTED)),
            range=[4, 11], tickfont=dict(color=TEXT_MUTED), gridcolor="#2E2E2E",
        ),
        yaxis=dict(
            title=dict(text="Annual Hrs Saved", font=dict(color=TEXT_MUTED)),
            tickfont=dict(color=TEXT_MUTED), gridcolor="#2E2E2E",
            range=[0, max_hrs * 1.4],
        ),
        margin=dict(l=60, r=30, t=20, b=60),
        height=420,
    )

    fig.add_shape(
        type="line", x0=7, x1=7, y0=0, y1=max_hrs * 1.35,
        line=dict(color=STONE, width=1, dash="dot"),
    )

    return fig


# ── SIDEBAR ──
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=180)
    st.markdown(
        f"<div style='margin-top:4px'>"
        f"<span style='color:{TEXT_WHITE};font-size:1.4rem;font-weight:800;letter-spacing:-0.02em'>EPM AI </span>"
        f"<span style='color:{DOORDASH_RED};font-size:1.4rem;font-weight:800;letter-spacing:-0.02em'>Leaderboard</span>"
        f"</div>"
        f"<p style='color:{TEXT_MUTED};font-size:0.8rem;margin-top:4px'>Grade SOPs. Size the value. Lead the charge.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    page = st.radio("Navigate", ["Dashboard", "Estimates vs. Actuals", "Log Team Usage", "Grade an SOP", "SOP Portfolio"], label_visibility="collapsed")

    st.divider()
    sops = load_all_sops()
    metrics = get_portfolio_metrics(sops)
    usage_logs_sidebar = load_usage_logs()
    remote_logs_sidebar = fetch_all_remote_usage()
    actuals_sidebar = get_team_metrics(usage_logs_sidebar + remote_logs_sidebar)
    local_logs_sidebar = scan_claude_code_logs()
    local_actuals_sidebar = compute_actuals(local_logs_sidebar)
    actual_hrs = actuals_sidebar["total_hours_saved"] + local_actuals_sidebar["total_actual_time_saved_hrs"]

    st.metric("SOPs Tracked", metrics["total_sops"])
    st.metric("Actual Hrs Saved", f"{actual_hrs:,.1f}")
    st.metric("Opportunity (annual)", f"{metrics['total_annual_hrs']:,.0f}")


# ── DASHBOARD ──
if page == "Dashboard":
    st.markdown(
        f"<h1 style='margin-bottom:0'>Team Automation Dashboard</h1>"
        f"<p style='color:{TEXT_MUTED};font-size:1.05rem;margin-top:4px'>"
        f"Actual savings vs. opportunity across <span style='color:{DOORDASH_RED};font-weight:700'>NAC-BD</span>"
        f"</p>",
        unsafe_allow_html=True,
    )

    sops = load_all_sops()
    metrics = get_portfolio_metrics(sops)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total SOPs", metrics["total_sops"])
    col2.metric("Avg Quality Grade", f"{metrics['avg_grade']}/10")
    col3.metric("Actual Hrs Saved", f"{actual_hrs:,.1f}")
    col4.metric("Opportunity (annual)", f"{metrics['total_annual_hrs']:,.0f}")
    col5.metric("People Impacted", metrics["total_people_impacted"])

    if sops:
        st.markdown("---")
        left, right = st.columns(2)

        with left:
            st.markdown("### Hours Recovered by SOP")
            st.plotly_chart(render_value_waterfall(sops), use_container_width=True)

        with right:
            st.markdown("### SOP Impact Map")
            st.plotly_chart(render_portfolio_scatter(sops), use_container_width=True)

        st.markdown("---")
        st.markdown("### Highest Opportunity")
        opp_left, opp_right = st.columns(2)
        with opp_left:
            st.markdown(f"**Biggest value driver:** {metrics['highest_value_sop']}")
        with opp_right:
            st.markdown(f"**Needs improvement:** {metrics['lowest_grade_sop']}")
            lowest = min(sops, key=lambda s: s["overall_grade"])
            if lowest.get("improvements"):
                for imp in lowest["improvements"]:
                    st.markdown(f"- {imp}")
    else:
        st.info("No SOPs graded yet. Go to **Grade an SOP** to get started.")


# ── ESTIMATES VS. ACTUALS ──
elif page == "Estimates vs. Actuals":
    st.markdown("# Estimates vs. Actuals")
    st.markdown(
        f"<p style='color:{TEXT_MUTED};font-size:1.1rem'>"
        "Projected savings from SOP grading vs. verified usage from Claude Code logs"
        "</p>",
        unsafe_allow_html=True,
    )

    sops = load_all_sops()
    metrics = get_portfolio_metrics(sops)

    log_dir = st.text_input("Claude Code log directory", value=os.path.expanduser("~/logs"), help="Path to the folder with merchant-refresh-*.log files")
    time_saved_input = st.number_input(
        "Manual minutes saved per agent run (what the task would take by hand)",
        min_value=1, max_value=300, value=40,
        help="How many minutes of manual work does each successful agent run replace?",
    )

    runs = scan_claude_code_logs(log_dir)
    actuals = compute_actuals(runs, time_saved_per_run_minutes=time_saved_input)

    st.markdown("---")

    est_col, act_col = st.columns(2)
    with est_col:
        st.markdown(f"### Estimated (from SOP grading)")
        e1, e2, e3 = st.columns(3)
        e1.metric("SOPs Graded", metrics["total_sops"])
        e2.metric("Weekly Hrs (projected)", f"{metrics['total_weekly_hrs']:,.0f}")
        e3.metric("Annual Hrs (projected)", f"{metrics['total_annual_hrs']:,.0f}")

    with act_col:
        st.markdown(f"### Actual (from logs)")
        a1, a2, a3 = st.columns(3)
        a1.metric("Agent Runs", actuals["total_runs"])
        a2.metric("Successful", actuals["successful_runs"])
        a3.metric("Hours Saved (verified)", f"{actuals['total_actual_time_saved_hrs']:.1f}")

    st.markdown("---")

    if actuals["total_runs"] > 0:
        detail_left, detail_right = st.columns(2)

        with detail_left:
            st.markdown("### Run History")

            run_dates = []
            run_statuses = []
            run_durations = []
            for r in actuals["runs"]:
                if r["started"]:
                    try:
                        dt = datetime.fromisoformat(r["started"])
                        run_dates.append(dt)
                        run_statuses.append("Success" if r["success"] else "Failed")
                        run_durations.append(r["duration_minutes"] or 0)
                    except (ValueError, TypeError):
                        pass

            if run_dates:
                fig = go.Figure()
                colors = [TIDE_POOL if s == "Success" else DOORDASH_RED for s in run_statuses]
                fig.add_trace(go.Bar(
                    x=run_dates,
                    y=run_durations,
                    marker=dict(color=colors),
                    text=[f"{d:.1f}m" for d in run_durations],
                    textposition="outside",
                    textfont=dict(color=TEXT_WHITE, size=10),
                    hovertemplate="<b>%{x}</b><br>Duration: %{y:.1f} min<extra></extra>",
                ))
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(tickfont=dict(color=TEXT_MUTED), gridcolor="#2E2E2E"),
                    yaxis=dict(
                        title=dict(text="Duration (min)", font=dict(color=TEXT_MUTED)),
                        tickfont=dict(color=TEXT_MUTED), gridcolor="#2E2E2E",
                    ),
                    margin=dict(l=50, r=20, t=20, b=40),
                    height=300,
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

        with detail_right:
            st.markdown("### Estimates vs. Actuals")

            estimated_monthly = metrics["total_weekly_hrs"] * 4.3
            actual_monthly = actuals["total_actual_time_saved_hrs"]

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=["Estimated (monthly)"], y=[estimated_monthly],
                marker=dict(color=FLUSH_LIGHT, opacity=0.7),
                text=[f"{estimated_monthly:,.0f} hrs"], textposition="outside",
                textfont=dict(color=TEXT_WHITE, size=12),
                name="Estimated",
            ))
            fig2.add_trace(go.Bar(
                x=["Actual (to date)"], y=[actual_monthly],
                marker=dict(color=TIDE_POOL),
                text=[f"{actual_monthly:,.1f} hrs"], textposition="outside",
                textfont=dict(color=TEXT_WHITE, size=12),
                name="Actual",
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickfont=dict(color=TEXT_WHITE, size=12), gridcolor="#2E2E2E"),
                yaxis=dict(
                    title=dict(text="Hours", font=dict(color=TEXT_MUTED)),
                    tickfont=dict(color=TEXT_MUTED), gridcolor="#2E2E2E",
                ),
                margin=dict(l=50, r=20, t=20, b=40),
                height=300,
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

            if estimated_monthly > 0:
                realization = (actual_monthly / estimated_monthly) * 100
                color = TIDE_POOL_LIGHT if realization >= 50 else LEMON if realization >= 20 else DOORDASH_RED
                st.markdown(
                    f"<div style='text-align:center;padding:16px;background:#1C1C1C;border-radius:12px;border:1px solid #2E2E2E'>"
                    f"<span style='color:{TEXT_MUTED};font-size:0.9rem'>Realization Rate</span><br>"
                    f"<span style='font-size:2.5rem;font-weight:800;color:{color}'>{realization:.0f}%</span><br>"
                    f"<span style='color:{TEXT_MUTED};font-size:0.8rem'>of projected savings verified</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.markdown("### Run Details")

        for r in reversed(actuals["runs"]):
            status = "✅" if r["success"] else "❌"
            dur = f"{r['duration_minutes']:.1f}m" if r["duration_minutes"] else "?"
            merchants = ", ".join(r["merchant_names"]) if r["merchant_names"] else "—"
            updated = r["merchants_updated"]
            started = r["started"][:16].replace("T", " ") if r["started"] else "Unknown"

            st.markdown(
                f"{status} **{started}** — {dur} — "
                f"{r['merchants_processed']} merchants ({updated} updated) — "
                f"`{r['filename']}`"
            )
    else:
        st.warning(
            f"No log files found in `{log_dir}` matching `merchant-refresh-*.log`. "
            "Run your first automated refresh to start tracking actuals."
        )

    # ── TEAM-REPORTED USAGE ──
    st.markdown("---")
    st.markdown("### Team-Wide Usage (Local + Google Sheets)")

    usage_logs = load_usage_logs()
    remote_logs = fetch_all_remote_usage()
    all_logs = usage_logs + remote_logs
    team_metrics = get_team_metrics(all_logs)

    src_local = len(usage_logs)
    src_remote = len(remote_logs)
    if src_remote > 0:
        st.caption(f"Showing {src_local} local entries + {src_remote} from Google Sheets = {len(all_logs)} total")

    if usage_logs:
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Usage Entries", team_metrics["total_logs"])
        t2.metric("Active People", f"{team_metrics['unique_people']}/{team_metrics['total_roster']}")
        t3.metric("Adoption", f"{team_metrics['adoption_pct']}%")
        t4.metric("Team Hours Saved", f"{team_metrics['total_hours_saved']:.1f}")

        if team_metrics["by_location"]:
            loc_left, loc_right = st.columns(2)
            with loc_left:
                st.markdown("#### Hours Saved by Location")
                locs = sorted(team_metrics["by_location"].items(), key=lambda x: x[1], reverse=True)
                loc_names, loc_mins = zip(*locs)
                loc_hrs = [m / 60 for m in loc_mins]
                fig_loc = go.Figure(go.Bar(
                    x=list(loc_hrs), y=list(loc_names), orientation="h",
                    marker=dict(color=DOORDASH_RED),
                    text=[f"{h:.1f} hrs" for h in loc_hrs],
                    textposition="outside",
                    textfont=dict(color=TEXT_WHITE, size=11),
                ))
                fig_loc.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(tickfont=dict(color=TEXT_MUTED), gridcolor="#2E2E2E"),
                    yaxis=dict(tickfont=dict(color=TEXT_WHITE, size=11), autorange="reversed"),
                    margin=dict(l=10, r=60, t=10, b=30), height=max(200, len(locs) * 40 + 60),
                    showlegend=False,
                )
                st.plotly_chart(fig_loc, use_container_width=True)

            with loc_right:
                st.markdown("#### Top Contributors")
                for rank, (person, mins) in enumerate(team_metrics["top_savers"][:8], 1):
                    hrs = mins / 60
                    bar_width = min(100, (mins / max(m for _, m in team_metrics["top_savers"])) * 100)
                    st.markdown(
                        f"<div style='margin-bottom:6px'>"
                        f"<span style='color:{TEXT_WHITE};font-size:0.9rem'>{rank}. {person}</span> "
                        f"<span style='color:{TEXT_MUTED};font-size:0.8rem'>({hrs:.1f} hrs)</span>"
                        f"<div style='background:#2E2E2E;border-radius:4px;height:8px;margin-top:2px'>"
                        f"<div style='background:{DOORDASH_RED};border-radius:4px;height:8px;width:{bar_width}%'></div>"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )

        # Combined realization
        combined_actual_hrs = actuals["total_actual_time_saved_hrs"] + team_metrics["total_hours_saved"]
        st.markdown("---")
        st.markdown("### Combined Realization (Logs + Team Reports)")
        c1, c2, c3 = st.columns(3)
        c1.metric("From Agent Logs", f"{actuals['total_actual_time_saved_hrs']:.1f} hrs")
        c2.metric("From Team Reports", f"{team_metrics['total_hours_saved']:.1f} hrs")
        c3.metric("Total Verified", f"{combined_actual_hrs:.1f} hrs")
    else:
        st.info(f"No team usage logged yet. Share the [Google Form]({GOOGLE_FORM_URL}) with your team or go to **Log Team Usage**.")

    st.markdown("---")
    st.markdown("### How Actuals Are Calculated")
    st.markdown(
        f"**Agent logs:** Each successful cron run replaces **{time_saved_input} minutes** of manual work. "
        f"With **{actuals['successful_runs']}** runs logged, that's **{actuals['total_actual_time_saved_hrs']:.1f} hours**.\n\n"
        f"**Team reports:** {team_metrics['total_logs']} entries from {team_metrics['unique_people']} people, "
        f"totaling **{team_metrics['total_hours_saved']:.1f} hours**.\n\n"
        f"Combined: **{actuals['total_actual_time_saved_hrs'] + team_metrics['total_hours_saved']:.1f} hours** verified "
        f"vs. **{metrics['total_annual_hrs']:,.0f} hrs/year** projected."
    )


# ── LOG TEAM USAGE ──
elif page == "Log Team Usage":
    st.markdown("# Log Team Usage")
    st.markdown(
        f"<p style='color:{TEXT_MUTED};font-size:1.1rem'>"
        "Quick-log when you or a teammate saves time with an AI automation"
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div style='background:linear-gradient(135deg,#1C1C1C,#242424);border:1px solid #2E2E2E;"
        f"border-radius:12px;padding:16px 20px;margin-bottom:20px'>"
        f"<b style='color:{TEXT_WHITE}'>Share with your team:</b> "
        f"<a href='{GOOGLE_FORM_URL}' style='color:{ACCENT_BLUE}'>Google Form</a> — "
        f"anyone can log usage without opening this dashboard. "
        f"Responses auto-sync here. "
        f"<a href='{GOOGLE_SHEET_URL}' style='color:{ACCENT_BLUE}'>View raw data</a>"
        f"</div>",
        unsafe_allow_html=True,
    )

    sops = load_all_sops()
    sop_lookup = {s["name"]: s for s in sops}

    existing_logs = load_usage_logs()
    logged_sop_names = sorted(set(l["sop_name"] for l in existing_logs))
    graded_sop_names = [s["name"] for s in sops]
    all_sop_names = list(dict.fromkeys(graded_sop_names + logged_sop_names))
    sop_options = all_sop_names + ["Other (type below)"]

    with st.form("log_usage_form", clear_on_submit=True):
        form_cols = st.columns(2)
        person = form_cols[0].selectbox("Who saved time?", TEAM_NAMES)
        sop_choice = form_cols[1].selectbox("Which SOP / automation?", sop_options)

        if sop_choice == "Other (type below)":
            custom_sop = st.text_input("SOP name", placeholder="e.g., Weekly QBR prep")
        else:
            custom_sop = ""

        matched_sop = sop_lookup.get(sop_choice)
        default_minutes = matched_sop["time_before_minutes"] - matched_sop["time_after_minutes"] if matched_sop else 30
        hint = f"(pre-filled from graded SOP: {matched_sop['time_before_minutes']}min before → {matched_sop['time_after_minutes']}min after)" if matched_sop else ""

        time_cols = st.columns(3)
        minutes_saved = time_cols[0].number_input("Minutes saved", min_value=1, max_value=480, value=max(1, default_minutes))
        notes = time_cols[1].text_input("Notes (optional)", placeholder="e.g., Prepped 3 merchant briefs")
        if hint:
            time_cols[2].markdown(f"<br><span style='color:{TEXT_MUTED};font-size:0.75rem'>{hint}</span>", unsafe_allow_html=True)

        submitted = st.form_submit_button("Log It", type="primary")
        if submitted:
            final_sop = custom_sop if sop_choice == "Other (type below)" else sop_choice
            if final_sop:
                entry = log_usage(person, final_sop, minutes_saved, notes)
                st.success(f"Logged **{minutes_saved} min** saved by **{person}** on **{final_sop}**")
            else:
                st.error("Please enter an SOP name.")

    # ── Team Scoreboard ──
    st.markdown("---")
    usage_logs = load_usage_logs()
    remote_logs = fetch_all_remote_usage()
    all_usage = usage_logs + remote_logs
    team_metrics = get_team_metrics(all_usage)

    st.markdown("### Team Scoreboard")

    if all_usage:
        sb1, sb2, sb3, sb4 = st.columns(4)
        sb1.metric("Total Entries", team_metrics["total_logs"])
        sb2.metric("People Active", f"{team_metrics['unique_people']}/{team_metrics['total_roster']}")
        sb3.metric("Adoption Rate", f"{team_metrics['adoption_pct']}%")
        sb4.metric("Total Hours Saved", f"{team_metrics['total_hours_saved']:.1f}")

        sb_left, sb_right = st.columns(2)
        with sb_left:
            st.markdown("#### Top Time Savers")
            for rank, (person, mins) in enumerate(team_metrics["top_savers"][:10], 1):
                hrs = mins / 60
                st.markdown(f"**{rank}.** {person} — {hrs:.1f} hrs")

        with sb_right:
            st.markdown("#### Most Used SOPs")
            for rank, (sop, mins) in enumerate(team_metrics["top_sops"][:10], 1):
                hrs = mins / 60
                st.markdown(f"**{rank}.** {sop} — {hrs:.1f} hrs")

        st.markdown("---")
        st.markdown("### Recent Entries")
        for entry in reversed(usage_logs[-20:]):
            ts = entry["timestamp"][:16].replace("T", " ")
            note_text = f" — *{entry['notes']}*" if entry.get("notes") else ""
            col_entry, col_del = st.columns([10, 1])
            with col_entry:
                st.markdown(
                    f"**{entry['person']}** saved **{entry['minutes_saved']} min** "
                    f"on *{entry['sop_name']}* ({ts}){note_text}"
                )
            with col_del:
                if st.button("✕", key=f"del_log_{entry['id']}"):
                    delete_usage_log(entry["id"])
                    st.rerun()
    else:
        st.info(f"No usage logged yet. Use the form above or share the [Google Form]({GOOGLE_FORM_URL}) with your team.")

    st.markdown("---")
    st.markdown(
        f"<p style='color:{TEXT_MUTED}'>"
        f"<b>{len(ROSTER)}</b> team members on the roster. "
        f"Not seeing someone? Edit <code>team.py</code> to update the roster."
        "</p>",
        unsafe_allow_html=True,
    )


# ── GRADE AN SOP ──
elif page == "Grade an SOP":
    st.markdown("# Grade an SOP")
    st.markdown(f"<p style='color:{TEXT_MUTED}'>Paste your SOP text below, then grade it with Claude or manually.</p>", unsafe_allow_html=True)

    st.markdown(
        f"<div style='background:{CARD_BG};border:1px solid {CARD_BORDER};"
        f"border-radius:12px;padding:16px 20px;margin-bottom:20px'>"
        f"<b style='color:{TEXT_WHITE}'>Want to skip this form?</b> "
        f"Anyone on the team can self-submit an SOP via "
        f"<a href='{SOP_FORM_URL}' style='color:{DOORDASH_RED}'>this Google Form</a> — "
        f"it auto-populates the leaderboard. No setup required."
        f"</div>",
        unsafe_allow_html=True,
    )

    name_cols = st.columns(2)
    sop_name = name_cols[0].text_input("SOP Name", placeholder="e.g., Automated Merchant Context File Refresh")
    built_by = name_cols[1].selectbox("Built by", [""] + TEAM_NAMES, format_func=lambda x: x if x else "Select who built this...")

    sop_raw = st.text_area(
        "Paste SOP Content (plain text or HTML — we'll clean it up)",
        height=300,
        placeholder="Paste the full SOP text here — HTML from Google Docs is fine, we strip the tags automatically...",
    )
    sop_text = clean_pasted_text(sop_raw) if sop_raw else ""

    if sop_raw and sop_raw != sop_text:
        st.caption(f"Cleaned {len(sop_raw):,} chars → {len(sop_text):,} chars (HTML tags & entities stripped)")
        with st.expander("Preview cleaned text", expanded=False):
            st.text(sop_text[:2000] + ("..." if len(sop_text) > 2000 else ""))

    team_size = st.number_input("Team size (people who use this SOP)", min_value=1, max_value=500, value=40)

    st.markdown("---")

    tab_auto, tab_manual = st.tabs(["⚡ Auto-Grade with Claude", "✏️ Manual Grade"])

    with tab_auto:
        api_key = st.text_input("Anthropic API Key", type="password", help="Your key is not stored. Only used for this grading call.")

        if st.button("Grade with Claude", type="primary", disabled=not (sop_name and sop_text and api_key)):
            with st.spinner("Claude is analyzing your SOP..."):
                try:
                    result = grade_sop(sop_text, api_key)
                    entry = add_sop(sop_name, team_size, result, sop_text, built_by=built_by)
                    st.success(f"Graded and saved! Overall: **{entry['overall_grade']}/10** — Annual savings: **{entry['annual_team_savings_hrs']:,.0f} hrs**")
                    st.balloons()

                    cols = st.columns(5)
                    for i, (k, v) in enumerate(result["scores"].items()):
                        with cols[i]:
                            render_grade_badge(v, k.replace("_", " ").title())

                    st.plotly_chart(render_radar_chart(result["scores"], sop_name), use_container_width=True)

                    if result.get("improvements"):
                        st.markdown("#### Improvement Suggestions")
                        for imp in result["improvements"]:
                            st.markdown(f"- {imp}")

                except Exception as e:
                    st.error(f"Grading failed: {e}")

    with tab_manual:
        st.markdown("Score each dimension 1-10:")
        mcols = st.columns(5)
        clarity = mcols[0].slider("Clarity", 1, 10, 7)
        completeness = mcols[1].slider("Completeness", 1, 10, 7)
        reproducibility = mcols[2].slider("Reproducibility", 1, 10, 7)
        automation = mcols[3].slider("Automation Potential", 1, 10, 7)
        doc_quality = mcols[4].slider("Doc Quality", 1, 10, 7)

        st.markdown("#### Time Estimates")
        tcols = st.columns(3)
        time_before = tcols[0].number_input("Minutes before (manual)", min_value=1, value=60)
        time_after = tcols[1].number_input("Minutes after (automated)", min_value=0, value=10)
        freq = tcols[2].number_input("Times per week", min_value=1, value=1)

        summary = st.text_input("Brief summary", placeholder="What does this SOP automate?")

        if st.button("Save Manual Grade", type="primary", disabled=not sop_name):
            scores = {
                "clarity": clarity,
                "completeness": completeness,
                "reproducibility": reproducibility,
                "automation_potential": automation,
                "documentation_quality": doc_quality,
            }
            meta = {
                "summary": summary,
                "time_before_minutes": time_before,
                "time_after_minutes": time_after,
                "frequency_per_week": freq,
                "improvements": [],
            }
            result = grade_sop_manual(scores, meta)
            entry = add_sop(sop_name, team_size, result, sop_text, built_by=built_by)
            st.success(f"Saved! Overall: **{entry['overall_grade']}/10** — Annual savings: **{entry['annual_team_savings_hrs']:,.0f} hrs**")
            st.balloons()


# ── SOP PORTFOLIO ──
elif page == "SOP Portfolio":
    st.markdown("# SOP Portfolio")
    st.markdown(f"<p style='color:{TEXT_MUTED}'>All graded SOPs with detailed breakdowns</p>", unsafe_allow_html=True)

    sops = load_all_sops()

    if not sops:
        st.info("No SOPs graded yet. Go to **Grade an SOP** to add your first.")
    else:
        for sop in sorted(sops, key=lambda s: s["annual_team_savings_hrs"], reverse=True):
            builder_tag = f" — Built by {sop['built_by']}" if sop.get("built_by") else ""
            with st.expander(f"**{sop['name']}**{builder_tag} — Grade: {sop['overall_grade']}/10 — {sop['annual_team_savings_hrs']:,.0f} hrs/year", expanded=False):
                st.markdown(f"*{sop.get('summary', 'No summary')}*")

                top_row = st.columns(5)
                for i, (k, v) in enumerate(sop["scores"].items()):
                    with top_row[i]:
                        render_grade_badge(v, k.replace("_", " ").title())

                st.markdown("---")

                val_cols = st.columns(4)
                val_cols[0].metric("Before", f"{sop['time_before_minutes']} min")
                val_cols[1].metric("After", f"{sop['time_after_minutes']} min")
                val_cols[2].metric("Frequency", f"{sop['frequency_per_week']}x/week")
                val_cols[3].metric("Team Size", sop["team_size"])

                sav_cols = st.columns(3)
                sav_cols[0].metric("Weekly (per person)", f"{sop['weekly_savings_per_person_hrs']} hrs")
                sav_cols[1].metric("Weekly (team)", f"{sop['weekly_team_savings_hrs']} hrs")
                sav_cols[2].metric("Annual (team)", f"{sop['annual_team_savings_hrs']:,.0f} hrs")

                chart_left, chart_right = st.columns(2)
                with chart_left:
                    st.plotly_chart(render_radar_chart(sop["scores"]), use_container_width=True)

                if sop.get("improvements"):
                    st.markdown("#### Improvements")
                    for imp in sop["improvements"]:
                        st.markdown(f"- {imp}")

                if st.button(f"Delete", key=f"del_{sop['id']}"):
                    delete_sop(sop["id"])
                    st.rerun()
