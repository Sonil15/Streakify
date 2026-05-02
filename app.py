"""
app.py
Main Streamlit entry point for Streakify.

Tabs:
  🏠 Dashboard     – streak overview + today's quick-log
  📋 Habits        – manage Spheres / Categories / Tasks
  👥 Accountability – view partner's progress (read-only)
  ⚙️ Settings      – profile, Telegram ID, link partner
"""

import streamlit as st
from dotenv import load_dotenv
from datetime import datetime

# Load .env for local dev (no-op on Streamlit Cloud)
load_dotenv()

import auth
import database as db
import streak_logic as sl
import ui_components as ui
import ai_planner
from dashboard_fragment import (
    invalidate_dashboard_bundle,
    render_dashboard_tasks_and_scoreboard,
)
from habits_fragment import invalidate_habits_bundle, render_habits_tab
from styles import inject_custom_css, COLORS

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Streakify 🔥",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Gate: require auth
# ---------------------------------------------------------------------------

inject_custom_css()
auth.flush_pending_persistent_login()
auth.try_restore_session()

if not auth.is_logged_in():
    auth.render_auth_page()
    st.stop()

# ---------------------------------------------------------------------------
# Auth is valid → load user info
# ---------------------------------------------------------------------------

user     = auth.get_current_user()
uid      = user["uid"]
dname    = user["display_name"]
today    = db.today_ist()
weekday  = datetime.strptime(today, "%Y-%m-%d").strftime("%A")
date_obj = datetime.strptime(today, "%Y-%m-%d").date()
pretty_date = date_obj.strftime("%d %b, %Y")

MOTIVATION_QUOTES = [
    "One small win today keeps your momentum strong.",
    "Show up today, and tomorrow gets easier.",
    "Consistency beats intensity every single time.",
    "Tiny actions compound into massive results.",
    "Progress, not perfection, keeps streaks alive.",
    "A 5-minute start can change your whole day.",
    "Discipline is just self-respect in action.",
    "Do the minimum, but never miss the day.",
    "Small promises kept build unshakable confidence.",
    "Your future self is built by today's habits.",
    "Keep the chain alive - even with one step.",
    "Momentum is earned in ordinary moments.",
    "Win the day first, then win the week.",
    "When motivation fades, routine carries you forward.",
]
quote_of_day = MOTIVATION_QUOTES[date_obj.toordinal() % len(MOTIVATION_QUOTES)]
EMOJI_OPTIONS = ["None", "💪", "🏃", "🧘", "🥗", "📚", "💼", "🧠", "💰", "🎯", "🛠️", "🎨", "📝", "🎵", "🧹", "🚴"]

# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------

tab_dash, tab_habits, tab_plan, tab_acct, tab_settings = st.tabs(
    ["🏠 Dashboard", "📋 Habits", "🧭 Grand Plan", "👥 Accountability", "⚙️ Settings"]
)


# ============================================================
# TAB 1 – DASHBOARD
# ============================================================
with tab_dash:
    st.markdown(
        f"""
        <div class='duo-hero'>
            <div class='duo-hero-title'>Hey {dname}, keep the streak alive 🔥</div>
            <div class='duo-hero-sub'>{quote_of_day}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='text-align:center;'><span class='duo-date-pill'>📅 {weekday}, {pretty_date} (IST)</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    spheres = db.get_spheres(uid)

    if not spheres:
        st.info(
            "🌱 You haven't created any Spheres yet! "
            "Head to the **📋 Habits** tab to get started."
        )
    else:
        # Today's tasks + scoreboard: isolated fragment (optimistic UI + async saves)
        render_dashboard_tasks_and_scoreboard(uid, dname, today)

        # ── Heatmaps ─────────────────────────────────────────────────
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-header'>Heatmaps</div>", unsafe_allow_html=True)

        for sphere in spheres:
            sid = sphere["id"]
            cats = db.get_categories(uid, sid)
            sphere_title = f"{sphere.get('emoji','')} {sphere.get('name','')}".strip()
            with st.expander(f"📂 {sphere_title}", expanded=False):
                if not cats:
                    st.caption("No categories in this sphere yet.")
                    continue
                for cat in cats:
                    history = db.get_completion_history(uid, sid, cat["id"], days=182)
                    ui.render_heatmap(
                        history,
                        title=f"{sphere.get('emoji','')} {sphere.get('name','')} › "
                              f"{cat.get('emoji','')} {cat.get('name','')}",
                        chart_key=f"heatmap_self_{sid}_{cat['id']}",
                    )


# ============================================================
# TAB 2 – HABITS MANAGEMENT
# ============================================================
with tab_habits:
    render_habits_tab(uid, EMOJI_OPTIONS, COLORS["text_muted"])


# ============================================================
# TAB 3 – GRAND PLAN
# ============================================================
with tab_plan:
    st.markdown("<div class='page-title'>🧭 Grand Plan</div>", unsafe_allow_html=True)
    st.caption("Write your long-term plan here. You can update it anytime.")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    profile = db.get_user_profile(uid) or {}
    current_plan = profile.get("grand_plan", "")

    with st.form("grand_plan_form"):
        plan_text = st.text_area(
            "Your Plan",
            value=current_plan,
            height=320,
            placeholder="Write your vision, milestones, and next steps...",
        )
        save_plan = st.form_submit_button("Save Grand Plan")

    if save_plan:
        db.update_user_profile(uid, {"grand_plan": plan_text.strip()})
        st.success("Grand Plan saved.")
        st.rerun()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### 🤖 AI Planner")
    st.caption(
        "Create-only assistant: it can add new categories/tasks from your plan. "
        "It will not create new spheres or delete anything."
    )
    ai_instruction = st.text_input(
        "Instruction for AI",
        value="Auto generate the tasks in my grand plan for the next week",
        placeholder="e.g. Create new category and tasks for next week from my grand plan",
    )

    if st.button("Generate Preview from Grand Plan"):
        latest_profile = db.get_user_profile(uid) or {}
        latest_plan = latest_profile.get("grand_plan", "")
        if not latest_plan.strip():
            st.error("Your Grand Plan is empty. Please add plan text first.")
        else:
            try:
                with st.spinner("AI is generating your weekly structure..."):
                    spheres = db.get_spheres(uid)
                    context = {"spheres": []}
                    for sphere in spheres:
                        sid = sphere["id"]
                        cats = db.get_categories(uid, sid)
                        context["spheres"].append(
                            {
                                "name": sphere.get("name", ""),
                                "emoji": sphere.get("emoji", ""),
                                "categories": [
                                    {
                                        "name": c.get("name", ""),
                                        "frequency": (c.get("frequency") or "daily").lower(),
                                        "tasks": [t.get("name", "") for t in db.get_tasks(uid, sid, c["id"])],
                                    }
                                    for c in cats
                                ],
                            }
                        )
                    generated = ai_planner.generate_structure(latest_plan, ai_instruction, context)
                    preview = ai_planner.get_creation_preview(uid, generated)
                st.session_state["ai_plan_generated"] = generated
                st.session_state["ai_plan_preview"] = preview
                st.session_state["ai_plan_instruction"] = ai_instruction
            except Exception as e:
                st.error(f"AI planner failed: {e}")

    preview = st.session_state.get("ai_plan_preview")
    generated = st.session_state.get("ai_plan_generated")
    if preview and generated:
        st.markdown("#### Preview")
        counts = preview.get("counts", {})
        st.info(
            f"Will create {counts.get('categories', 0)} categories, "
            f"{counts.get('tasks', 0)} tasks. "
            f"Will skip {counts.get('spheres_skipped_missing', 0)} unknown spheres."
        )

        for s in preview.get("spheres_skipped_missing", []):
            label = f"{s.get('emoji','')} {s.get('name','')}".strip()
            st.markdown(f"- Skipped unknown sphere (not created): **{label}**")
        for c in preview.get("categories_to_create", []):
            label = f"{c.get('emoji','')} {c.get('name','')}".strip()
            st.markdown(
                f"- New category in **{c.get('sphere','')}**: "
                f"**{label}** ({c.get('frequency','daily')})"
            )

        with st.expander("Tasks to create", expanded=False):
            for t in preview.get("tasks_to_create", []):
                st.markdown(
                    f"- **{t.get('sphere','')} › {t.get('category','')}**: {t.get('name','')}"
                )

        col_apply, col_clear = st.columns([2, 1])
        with col_apply:
            if st.button("Apply Proposed Changes"):
                try:
                    summary = ai_planner.apply_generated_structure(uid, generated)
                    st.success(
                        "AI plan applied. "
                        f"Created {summary['categories_created']} categories, "
                        f"{summary['tasks_created']} tasks. "
                        f"Skipped {summary['tasks_skipped_existing']} existing tasks and "
                        f"{summary['spheres_skipped_missing']} unknown spheres."
                    )
                    st.session_state.pop("ai_plan_generated", None)
                    st.session_state.pop("ai_plan_preview", None)
                    st.session_state.pop("ai_plan_instruction", None)
                    invalidate_dashboard_bundle()
                    invalidate_habits_bundle()
                    st.rerun()
                except Exception as e:
                    st.error(f"Apply failed: {e}")
        with col_clear:
            if st.button("Discard Preview"):
                st.session_state.pop("ai_plan_generated", None)
                st.session_state.pop("ai_plan_preview", None)
                st.session_state.pop("ai_plan_instruction", None)
                st.rerun()


# ============================================================
# TAB 4 – ACCOUNTABILITY
# ============================================================
with tab_acct:
    st.markdown("<div class='page-title'>👥 Accountability Partner</div>", unsafe_allow_html=True)
    st.caption("Stay motivated by watching each other's progress — read-only view.")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    profile = db.get_user_profile(uid)
    partner_id = (profile or {}).get("accountability_partner_id", "")

    # ── Link / change partner ─────────────────────────────────────
    with st.expander("🔗 Link Accountability Partner", expanded=not partner_id):
        with st.form("link_partner_form"):
            partner_email = st.text_input(
                "Partner's Email",
                placeholder="friend@example.com",
                help="They must have a Streakify account.",
            )
            link_submit = st.form_submit_button("Link Partner 🤝")

        if link_submit:
            if not partner_email.strip():
                st.error("Please enter an email.")
            else:
                found = db.find_user_by_email(partner_email.strip().lower())
                if not found:
                    st.error("No Streakify account found for that email.")
                elif found["uid"] == uid:
                    st.error("You can't add yourself as a partner 😅")
                else:
                    db.update_user_profile(uid, {"accountability_partner_id": found["uid"]})
                    st.success(
                        f"Linked with **{found.get('display_name', partner_email)}**! 🎉"
                    )
                    st.rerun()

        if partner_id:
            if st.button("❌ Unlink current partner"):
                db.update_user_profile(uid, {"accountability_partner_id": ""})
                st.rerun()

    # ── Partner view ─────────────────────────────────────────────
    if not partner_id:
        st.info("Link an accountability partner above to see their progress here.")
    else:
        partner_profile = db.get_user_profile(partner_id)
        if not partner_profile:
            st.warning("Partner account not found. They may have deleted it.")
        else:
            # Build partner's spheres with categories
            partner_spheres = db.get_spheres(partner_id)
            spheres_with_cats = []
            completion_today_map: dict[str, bool] = {}

            for sphere in partner_spheres:
                sid  = sphere["id"]
                cats = db.get_categories(partner_id, sid)

                # Reconcile each category (so their streaks are accurate)
                cats_reconciled = []
                for cat in cats:
                    cat = sl.reconcile_streak(partner_id, sid, cat)
                    cats_reconciled.append(cat)

                    # Check today's completion for the map
                    comp = db.get_completion(partner_id, sid, cat["id"], today)
                    done = len(comp.get("completed_tasks", [])) > 0
                    completion_today_map[f"{sid}:{cat['id']}"] = done

                sphere["categories"] = cats_reconciled
                spheres_with_cats.append(sphere)

            ui.render_accountability_view(
                partner_profile,
                spheres_with_cats,
                completion_today_map,
            )

            # ── Partner heatmaps (read-only) ──────────────────────
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            st.markdown("<div class='section-header'>Partner Heatmaps</div>", unsafe_allow_html=True)

            for sphere in partner_spheres:
                sid = sphere["id"]
                cats = db.get_categories(partner_id, sid)
                sphere_title = f"{sphere.get('emoji','')} {sphere.get('name','')}".strip()
                with st.expander(f"📂 {sphere_title}", expanded=False):
                    if not cats:
                        st.caption("No categories in this sphere yet.")
                        continue
                    for cat in cats:
                        history = db.get_completion_history(partner_id, sid, cat["id"], days=182)
                        ui.render_heatmap(
                            history,
                            title=f"{sphere.get('emoji','')} {sphere.get('name','')} › "
                                  f"{cat.get('emoji','')} {cat.get('name','')}",
                            chart_key=f"heatmap_partner_{sid}_{cat['id']}",
                        )


# ============================================================
# TAB 5 – SETTINGS
# ============================================================
with tab_settings:
    st.markdown("<div class='page-title'>⚙️ Settings</div>", unsafe_allow_html=True)
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    profile = db.get_user_profile(uid)
    if not profile:
        st.error("Could not load profile.")
        st.stop()

    # ── Profile ─────────────────────────────────────────────────
    st.markdown("### 👤 Profile")
    with st.form("profile_form"):
        new_name = st.text_input("Display Name", value=profile.get("display_name", ""))
        save_profile = st.form_submit_button("Save Profile")

    if save_profile:
        if new_name.strip():
            db.update_user_profile(uid, {"display_name": new_name.strip()})
            st.session_state["display_name"] = new_name.strip()
            st.success("Profile updated! ✅")
            st.rerun()
        else:
            st.error("Name can't be empty.")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── Telegram ─────────────────────────────────────────────────
    st.markdown("### 🤖 Telegram Reminders")
    st.info(
        "💡 To find your Telegram Chat ID:\n"
        "1. Search for **@userinfobot** on Telegram.\n"
        "2. Start the bot and it will reply with your Chat ID.\n"
        "3. Paste it below and save.",
        icon="ℹ️",
    )

    with st.form("telegram_form"):
        tg_id = st.text_input(
            "Your Telegram Chat ID",
            value=profile.get("telegram_chat_id", ""),
            placeholder="e.g. 123456789",
        )
        save_tg = st.form_submit_button("Save Telegram ID 💾")

    if save_tg:
        db.update_user_profile(uid, {"telegram_chat_id": tg_id.strip()})
        st.success("Telegram Chat ID saved! You'll now receive reminder notifications. 🔔")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── Account info ─────────────────────────────────────────────
    st.markdown("### 📧 Account Info")
    st.markdown(
        f"""
        <div class="streak-card">
            <div style="color:{COLORS['text_muted']}; font-size:0.85rem; font-weight:600;">EMAIL</div>
            <div style="font-weight:800; font-size:1.1rem; color:{COLORS['text_main']}; margin-top:4px;">
                {profile.get('email', '')}
            </div>
            <div style="color:{COLORS['text_muted']}; font-size:0.85rem; font-weight:600; margin-top:10px;">USER ID</div>
            <div style="font-weight:600; font-size:0.9rem; color:{COLORS['text_muted']}; margin-top:4px; font-family:monospace;">
                {uid}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Share your email with someone to let them add you as an accountability partner.")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    if st.button("🚪 Logout"):
        auth.logout()
        st.rerun()
