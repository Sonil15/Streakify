"""
ui_components.py
Reusable UI building blocks:
  - streak cards
  - freeze badges
  - GitHub-style contribution heatmap (Plotly)
  - task checklist
  - category summary row
  - accountability read-only view
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
from styles import COLORS
import streak_logic as sl


# ---------------------------------------------------------------------------
# Streak card (renders raw HTML via st.markdown)
# ---------------------------------------------------------------------------

def render_streak_card(category: dict, show_progress: bool = True):
    """Render a cute streak card for a single category."""
    name   = category.get("name", "")
    emoji  = category.get("emoji", "📌")
    streak = category.get("streak", 0)
    freeze = category.get("freeze_count", 0)
    consec = category.get("consecutive_days", 0)

    color          = sl.streak_color(streak)
    streak_icon    = sl.streak_emoji(streak)
    freeze_text    = sl.freeze_display(freeze)
    days_to_freeze = sl.days_until_next_freeze(consec)

    st.markdown(
        f"""
        <div class="streak-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <div style="font-size:1.3rem; font-weight:800; color:{COLORS['text_main']};">
                        {emoji} {name}
                    </div>
                    <div style="margin-top:6px;">
                        <span class="streak-number" style="color:{color};">
                            {streak}
                        </span>
                        <span class="streak-label"> day streak {streak_icon}</span>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div class="freeze-badge">{freeze_text}</div>
                    <div style="font-size:0.78rem; color:{COLORS['text_muted']}; margin-top:6px;">
                        {days_to_freeze}d until next ❄️
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if show_progress and consec > 0:
        pct = (consec % 7) / 7
        if pct == 0 and consec > 0:
            pct = 1.0
        st.progress(pct, text=f"🎯 {consec % 7 or 7}/7 days towards next ❄️")


# ---------------------------------------------------------------------------
# Mini stat row (used in accountability view)
# ---------------------------------------------------------------------------

def render_mini_stat_row(label: str, value, icon: str = ""):
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; padding:6px 0;
                    border-bottom:1px solid {COLORS['border']};">
            <span style="color:{COLORS['text_muted']}; font-weight:600;">{icon} {label}</span>
            <span style="font-weight:800; color:{COLORS['text_main']};">{value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# GitHub-style heatmap
# ---------------------------------------------------------------------------

def render_heatmap(history: dict[str, bool], title: str, weeks: int = 26):
    """
    Cleaner GitHub-style heatmap:
    - sparse month labels (no overlap)
    - title rendered outside plot
    - square-ish cells and better margins
    """
    today = date.today()
    start = today - timedelta(weeks=weeks)

    # Sunday on or before start
    offset = (start.weekday() + 1) % 7  # Mon=0..Sun=6
    grid_start = start - timedelta(days=offset)

    total_cols = weeks + 2
    z = [[None] * total_cols for _ in range(7)]
    labels = [[""] * total_cols for _ in range(7)]

    # Build sparse x ticks: first week of each month only
    tickvals = []
    ticktext = []

    for col in range(total_cols):
        week_start = grid_start + timedelta(weeks=col)

        if week_start.day <= 7:
            tickvals.append(col)
            ticktext.append(week_start.strftime("%b"))

        for row in range(7):
            day = week_start + timedelta(days=row)
            if day > today:
                continue

            ds = day.strftime("%Y-%m-%d")
            done = history.get(ds, False)
            z[row][col] = 1 if done else 0.18
            labels[row][col] = f"{'✅' if done else '○'} {ds}"

    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    # Render title outside plot to avoid overlap
    st.markdown(f"**{title}**")

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=list(range(total_cols)),
            y=day_names,
            text=labels,
            hovertemplate="%{text}<extra></extra>",
            colorscale=[
                [0.00, "#F3F3F8"],          # empty / future
                [0.18, "#E8E0FF"],          # no completion
                [1.00, COLORS["primary"]],  # completed
            ],
            zmin=0,
            zmax=1,
            showscale=False,
            xgap=3,
            ygap=3,
        )
    )

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=40, r=10, t=8, b=18),
        height=180,
        xaxis=dict(
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=10, family="Nunito"),
            side="top",
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=10, family="Nunito"),
            autorange="reversed",
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# Task checklist
# ---------------------------------------------------------------------------

def render_task_checklist(
    tasks: list[dict],
    completed_ids: list[str],
    key_prefix: str,
    readonly: bool = False,
) -> tuple[list[str], list[str]]:
    """
    Render a set of checkboxes for the given tasks.
    Returns (newly_checked_ids, newly_unchecked_ids) relative to the initial state.
    When readonly=True, all boxes are disabled.
    """
    newly_checked:   list[str] = []
    newly_unchecked: list[str] = []

    if not tasks:
        st.caption("No tasks yet — add one below! 👇")
        return newly_checked, newly_unchecked

    for task in tasks:
        tid   = task["id"]
        tname = task.get("name", "")
        was_done = tid in completed_ids
        key      = f"{key_prefix}_{tid}"

        if readonly:
            icon = "✅" if was_done else "⬜"
            st.markdown(f"{icon} &nbsp; {tname}", unsafe_allow_html=True)
        else:
            checked = st.checkbox(
                tname,
                value=was_done,
                key=key,
                disabled=readonly,
            )
            if checked and not was_done:
                newly_checked.append(tid)
            elif not checked and was_done:
                newly_unchecked.append(tid)

    return newly_checked, newly_unchecked


# ---------------------------------------------------------------------------
# Sphere overview card (used in dashboard)
# ---------------------------------------------------------------------------

def render_sphere_overview(sphere: dict, categories: list[dict]):
    """Render a collapsible sphere section with category streak rows."""
    sname = sphere.get("name", "")
    semoji = sphere.get("emoji", "🌀")

    with st.expander(f"{semoji} **{sname}**", expanded=True):
        if not categories:
            st.caption("No categories yet.")
            return

        for cat in categories:
            col1, col2, col3 = st.columns([4, 2, 2])
            streak = cat.get("streak", 0)
            freeze = cat.get("freeze_count", 0)
            with col1:
                st.markdown(
                    f"**{cat.get('emoji','📌')} {cat.get('name','')}**",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"<span style='color:{sl.streak_color(streak)};font-weight:800;'>"
                    f"{sl.streak_emoji(streak)} {streak} days</span>",
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f"<span class='freeze-badge'>{sl.freeze_display(freeze)}</span>",
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Accountability read-only view
# ---------------------------------------------------------------------------

def render_accountability_view(
    partner_profile: dict,
    spheres_with_categories: list[dict],
    completion_today_map: dict,   # {sphere_id_cat_id: bool}
):
    """
    Render a read-only overview of the partner's data.
    `completion_today_map` keys are f"{sphere_id}:{category_id}".
    """
    name = partner_profile.get("display_name", "Your Partner")
    email = partner_profile.get("email", "")

    st.markdown(
        f"""
        <div class="readonly-banner">
            👀 Viewing <strong>{name}</strong>'s progress ({email}) — Read-only mode
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not spheres_with_categories:
        st.info("Your accountability partner hasn't set up any spheres yet.")
        return

    for sphere in spheres_with_categories:
        semoji = sphere.get("emoji", "🌀")
        sname  = sphere.get("name", "")
        cats   = sphere.get("categories", [])

        with st.expander(f"{semoji} **{sname}**", expanded=True):
            for cat in cats:
                ckey      = f"{sphere['id']}:{cat['id']}"
                done_today = completion_today_map.get(ckey, False)
                streak     = cat.get("streak", 0)
                freeze     = cat.get("freeze_count", 0)

                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                with col1:
                    st.markdown(f"**{cat.get('emoji','📌')} {cat.get('name','')}**")
                with col2:
                    st.markdown(
                        f"<span style='color:{sl.streak_color(streak)};font-weight:800;'>"
                        f"{sl.streak_emoji(streak)} {streak}d</span>",
                        unsafe_allow_html=True,
                    )
                with col3:
                    st.markdown(
                        f"<span class='freeze-badge'>{sl.freeze_display(freeze)}</span>",
                        unsafe_allow_html=True,
                    )
                with col4:
                    badge_color = COLORS["success"] if done_today else COLORS["danger"]
                    badge_text  = "✅ Done" if done_today else "🔴 Pending"
                    st.markdown(
                        f"<span style='color:{badge_color}; font-weight:700;'>{badge_text}</span>",
                        unsafe_allow_html=True,
                    )
