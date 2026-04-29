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

# ---------------------------------------------------------------------------
# Top navigation bar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"""
        <div class='streak-card' style='padding:14px 12px;'>
            <div style='font-size:2.2rem;'>🔥</div>
            <div style='font-size:1.25rem; font-weight:900; color:{COLORS["primary"]};'>Streakify</div>
            <div style='font-size:0.84rem; color:{COLORS["text_muted"]}; margin-top:4px;'>
                Hi, {dname}! 👋
            </div>
            <div class='duo-chip-row'>
                <span class='duo-chip'>⚡ Consistency</span>
                <span class='duo-chip'>❄️ Freezes</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border-color:#E8E8F0;'>", unsafe_allow_html=True)

    if st.button("🚪 Logout", use_container_width=True):
        auth.logout()
        st.rerun()

# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------

tab_dash, tab_habits, tab_acct, tab_settings = st.tabs(
    ["🏠 Dashboard", "📋 Habits", "👥 Accountability", "⚙️ Settings"]
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
        # ── Daily quick-log ──────────────────────────────────────────
        st.markdown("### Today's Tasks", unsafe_allow_html=True)
        st.caption("Check off at least one task per category to keep your streak alive!")

        any_new_completion = False

        for sphere in spheres:
            sid   = sphere["id"]
            cats  = db.get_categories(uid, sid)
            if not cats:
                continue

            st.markdown(
                f"<div class='section-header'>{sphere.get('emoji','🌀')} {sphere.get('name','')}</div>",
                unsafe_allow_html=True,
            )

            for cat in cats:
                cid   = cat["id"]
                tasks = db.get_tasks(uid, sid, cid)
                frequency = (cat.get("frequency") or "daily").lower()
                cadence_label = "week" if frequency == "weekly" else "day"

                # Reconcile streak (handles missed days automatically)
                cat = sl.reconcile_streak(uid, sid, cat)

                completion_doc    = db.get_completion(uid, sid, cid, today)
                completed_ids     = completion_doc.get("completed_tasks", [])
                is_done_today     = len(completed_ids) > 0

                card_color = COLORS["success"] if is_done_today else COLORS["border"]
                status_icon = "✅" if is_done_today else "⬜"

                with st.expander(
                    f"{cat.get('emoji','📌')} **{cat.get('name','')}** — "
                    f"{sl.streak_emoji(cat.get('streak',0))} **{cat.get('streak',0)} {cadence_label} streak** "
                    f"| {sl.freeze_display(cat.get('freeze_count',0))} "
                    f"| {status_icon}",
                    expanded=not is_done_today,
                ):
                    if not tasks:
                        st.caption("No tasks yet — add some in the Habits tab!")
                        continue

                    key_pfx = f"dash_{sid}_{cid}"
                    newly_checked, newly_unchecked = ui.render_task_checklist(
                        tasks, completed_ids, key_prefix=key_pfx
                    )

                    # Process newly checked
                    for tid in newly_checked:
                        db.set_task_completion(uid, sid, cid, tid, today, True)
                        completed_ids.append(tid)

                    # Process newly unchecked
                    for tid in newly_unchecked:
                        db.set_task_completion(uid, sid, cid, tid, today, False)
                        completed_ids.remove(tid)

                    # After any change, refresh streak
                    if newly_checked:
                        cat = sl.record_completion_for_today(uid, sid, cat)
                        any_new_completion = True
                        if cat.get("freeze_awarded_today"):
                            st.success(
                                f"🎉 You earned a new ❄️ Freeze for **{cat['name']}**! "
                                f"You now have {cat['freeze_count']} freezes."
                            )

                    if newly_unchecked:
                        cat = sl.check_if_still_active_today(
                            uid, sid, cid, completed_ids, cat
                        )

                    # Progress bar: tasks done / total
                    pct = len(completed_ids) / len(tasks) if tasks else 0
                    st.progress(pct, text=f"{len(completed_ids)}/{len(tasks)} tasks done today")

        # Celebrate!
        if any_new_completion:
            st.balloons()

        # ── Streak overview ──────────────────────────────────────────
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.markdown("### 🏆 Streak Scoreboard", unsafe_allow_html=True)

        all_cats_flat = []
        for sphere in spheres:
            for cat in db.get_categories(uid, sphere["id"]):
                cat["sphere_name"]  = sphere.get("name", "")
                cat["sphere_emoji"] = sphere.get("emoji", "")
                all_cats_flat.append(cat)

        if all_cats_flat:
            # Sort by streak descending
            all_cats_flat.sort(key=lambda c: c.get("streak", 0), reverse=True)
            cols = st.columns(min(len(all_cats_flat), 3))
            for idx, cat in enumerate(all_cats_flat):
                with cols[idx % 3]:
                    ui.render_streak_card(cat)

        # ── Heatmaps ─────────────────────────────────────────────────
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-header'>Heatmaps</div>", unsafe_allow_html=True)

        for sphere in spheres:
            sid  = sphere["id"]
            cats = db.get_categories(uid, sid)
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
    st.markdown("<div class='page-title'>📋 Manage Habits</div>", unsafe_allow_html=True)
    st.caption("Create Spheres → Categories → Tasks. Streaks are tracked at the Category level.")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── Create Sphere ──────────────────────────────────────────────
    with st.expander("➕ Add New Sphere", expanded=False):
        with st.form("create_sphere_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_sphere_name = st.text_input("Sphere Name", placeholder="e.g. Health, Career, Prep")
            with col2:
                new_sphere_emoji = st.text_input("Emoji", placeholder="🌿", max_chars=4)
            submitted = st.form_submit_button("Create Sphere 🌀", use_container_width=True)

        if submitted:
            if not new_sphere_name.strip():
                st.error("Please enter a name.")
            else:
                db.create_sphere(uid, new_sphere_name.strip(), new_sphere_emoji.strip() or "🌀")
                st.success(f"Sphere '{new_sphere_name}' created! 🎉")
                st.rerun()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    spheres = db.get_spheres(uid)
    if not spheres:
        st.info("No spheres yet! Create one above ⬆️")
    else:
        for sphere in spheres:
            sid     = sphere["id"]
            sname   = sphere.get("name", "")
            semoji  = sphere.get("emoji", "🌀")

            with st.expander(f"{semoji} **{sname}**", expanded=True):
                # Sphere actions
                scol1, scol2 = st.columns([6, 1])
                with scol2:
                    if st.button("🗑️", key=f"del_sphere_{sid}", help="Delete this sphere"):
                        db.delete_sphere(uid, sid)
                        st.success(f"Sphere '{sname}' deleted.")
                        st.rerun()

                # ── Add category ────────────────────────────────────
                with st.form(f"add_cat_{sid}"):
                    st.markdown("**Add Category:**")
                    cc1, cc2, cc3, cc4 = st.columns([3, 1, 2, 1])
                    with cc1:
                        cat_name = st.text_input("Category Name", placeholder="e.g. Diet, Coding", key=f"cn_{sid}")
                    with cc2:
                        cat_emoji = st.text_input("Emoji", placeholder="🥗", max_chars=4, key=f"ce_{sid}")
                    with cc3:
                        cat_frequency = st.selectbox(
                            "Cadence",
                            options=["Daily", "Weekly"],
                            key=f"cf_{sid}",
                        )
                    with cc4:
                        st.markdown("<br>", unsafe_allow_html=True)
                        cat_submit = st.form_submit_button("Add ➕")

                    if cat_submit:
                        if not cat_name.strip():
                            st.error("Category name required.")
                        else:
                            db.create_category(
                                uid,
                                sid,
                                cat_name.strip(),
                                cat_emoji.strip() or "📌",
                                frequency=cat_frequency.lower(),
                            )
                            st.success(f"Category '{cat_name}' added!")
                            st.rerun()

                # ── Existing categories ──────────────────────────────
                cats = db.get_categories(uid, sid)
                for cat in cats:
                    cid    = cat["id"]
                    cname  = cat.get("name", "")
                    cemoji = cat.get("emoji", "📌")

                    st.markdown(
                        f"<div style='margin-top:12px; font-weight:700; font-size:1.05rem;'>"
                        f"{cemoji} {cname}"
                        f"<span style='font-size:0.8rem; font-weight:400; color:{COLORS['text_muted']}; margin-left:8px;'>"
                        f"🔥 {cat.get('streak',0)} streak"
                        f" ({'weekly' if (cat.get('frequency') or 'daily').lower() == 'weekly' else 'daily'})"
                        f" | ❄️ {cat.get('freeze_count',0)} freezes"
                        f"</span></div>",
                        unsafe_allow_html=True,
                    )

                    tasks = db.get_tasks(uid, sid, cid)

                    # Add task form
                    with st.form(f"add_task_{sid}_{cid}"):
                        t1, t2 = st.columns([5, 1])
                        with t1:
                            task_name = st.text_input(
                                "New Task", placeholder="e.g. Eat 100g protein",
                                key=f"tn_{sid}_{cid}", label_visibility="collapsed"
                            )
                        with t2:
                            task_submit = st.form_submit_button("Add Task")

                        if task_submit:
                            if task_name.strip():
                                db.create_task(uid, sid, cid, task_name.strip())
                                st.success("Task added!")
                                st.rerun()

                    # List existing tasks
                    for task in tasks:
                        tcol1, tcol2 = st.columns([8, 1])
                        with tcol1:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;• {task.get('name','')}", unsafe_allow_html=True)
                        with tcol2:
                            if st.button("✕", key=f"del_task_{sid}_{cid}_{task['id']}"):
                                db.delete_task(uid, sid, cid, task["id"])
                                st.rerun()

                    # Delete category button
                    if st.button(f"🗑️ Remove '{cname}'", key=f"del_cat_{sid}_{cid}"):
                        db.delete_category(uid, sid, cid)
                        st.success(f"Category '{cname}' deleted.")
                        st.rerun()

                    st.markdown("<hr style='border-color:#F0F0F0; margin:10px 0;'>", unsafe_allow_html=True)


# ============================================================
# TAB 3 – ACCOUNTABILITY
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
            link_submit = st.form_submit_button("Link Partner 🤝", use_container_width=True)

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
                sid  = sphere["id"]
                cats = db.get_categories(partner_id, sid)
                for cat in cats:
                    history = db.get_completion_history(partner_id, sid, cat["id"], days=182)
                    ui.render_heatmap(
                        history,
                        title=f"{sphere.get('emoji','')} {sphere.get('name','')} › "
                              f"{cat.get('emoji','')} {cat.get('name','')}",
                        chart_key=f"heatmap_partner_{sid}_{cat['id']}",
                    )


# ============================================================
# TAB 4 – SETTINGS
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
        save_profile = st.form_submit_button("Save Profile", use_container_width=True)

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
        save_tg = st.form_submit_button("Save Telegram ID 💾", use_container_width=True)

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
