"""
Habits tab fragment with cached bundle to avoid heavy full-app reruns.
"""

from __future__ import annotations

import streamlit as st

import database as db
from dashboard_fragment import invalidate_dashboard_bundle
from habits_bundle import build_habits_bundle

HABITS_BUNDLE_KEY = "_habits_bundle"


def invalidate_habits_bundle() -> None:
    st.session_state.pop(HABITS_BUNDLE_KEY, None)


def _ensure_habits_bundle(uid: str) -> dict:
    cached = st.session_state.get(HABITS_BUNDLE_KEY)
    if cached and cached.get("uid") == uid:
        return cached
    b = build_habits_bundle(uid)
    st.session_state[HABITS_BUNDLE_KEY] = b
    return b


@st.fragment
def render_habits_tab(uid: str, emoji_options: list[str], text_muted: str) -> None:
    st.markdown("<div class='page-title'>📋 Manage Habits</div>", unsafe_allow_html=True)
    st.caption("Create Spheres → Categories → Tasks. Streaks are tracked at the Category level.")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    with st.expander("➕ Add New Sphere", expanded=False):
        with st.form("create_sphere_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_sphere_name = st.text_input(
                    "Sphere Name", placeholder="e.g. Health, Career, Prep"
                )
            with col2:
                new_sphere_emoji_choice = st.selectbox("Emoji", options=emoji_options)
            submitted = st.form_submit_button("Create Sphere 🌀")

        if submitted:
            if not new_sphere_name.strip():
                st.error("Please enter a name.")
            else:
                new_sphere_emoji = (
                    "" if new_sphere_emoji_choice == "None" else new_sphere_emoji_choice
                )
                db.create_sphere(uid, new_sphere_name.strip(), new_sphere_emoji)
                invalidate_habits_bundle()
                invalidate_dashboard_bundle()
                st.success(f"Sphere '{new_sphere_name}' created! 🎉")
                st.rerun(scope="fragment")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    bundle = _ensure_habits_bundle(uid)
    rows = bundle.get("spheres", [])
    if not rows:
        st.info("No spheres yet! Create one above ⬆️")
        return

    for row in rows:
        sphere = row["sphere"]
        cats = row["categories"]
        sid = sphere["id"]
        sname = sphere.get("name", "")
        semoji = sphere.get("emoji", "")
        sphere_label = f"{semoji} {sname}".strip()

        with st.expander(f"**{sphere_label}**", expanded=True):
            scol1, scol2 = st.columns([6, 1])
            with scol2:
                if st.button("🗑️", key=f"del_sphere_{sid}", help="Delete this sphere"):
                    db.delete_sphere(uid, sid)
                    invalidate_habits_bundle()
                    invalidate_dashboard_bundle()
                    st.success(f"Sphere '{sname}' deleted.")
                    st.rerun(scope="fragment")

            with st.form(f"add_cat_{sid}"):
                st.markdown("**Add Category:**")
                cc1, cc2, cc3, cc4 = st.columns([3, 1, 2, 1])
                with cc1:
                    cat_name = st.text_input(
                        "Category Name",
                        placeholder="e.g. Diet, Coding",
                        key=f"cn_{sid}",
                    )
                with cc2:
                    cat_emoji_choice = st.selectbox(
                        "Emoji", options=emoji_options, key=f"ce_{sid}"
                    )
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
                        cat_emoji = (
                            "" if cat_emoji_choice == "None" else cat_emoji_choice
                        )
                        db.create_category(
                            uid,
                            sid,
                            cat_name.strip(),
                            cat_emoji,
                            frequency=cat_frequency.lower(),
                        )
                        invalidate_habits_bundle()
                        invalidate_dashboard_bundle()
                        st.success(f"Category '{cat_name}' added!")
                        st.rerun(scope="fragment")

            for cat in cats:
                cid = cat["id"]
                cname = cat.get("name", "")
                cemoji = cat.get("emoji", "")
                cat_label = f"{cemoji} {cname}".strip()

                st.markdown(
                    f"<div style='margin-top:12px; font-weight:700; font-size:1.05rem;'>"
                    f"{cat_label}"
                    f"<span style='font-size:0.8rem; font-weight:400; color:{text_muted}; margin-left:8px;'>"
                    f"🔥 {cat.get('streak',0)} streak"
                    f" ({'weekly' if (cat.get('frequency') or 'daily').lower() == 'weekly' else 'daily'})"
                    f" | {'No freezes' if (cat.get('frequency') or 'daily').lower() == 'weekly' else f'❄️ {cat.get('freeze_count',0)} freezes'}"
                    f"</span></div>",
                    unsafe_allow_html=True,
                )

                tasks = cat.get("tasks", [])
                with st.form(f"add_task_{sid}_{cid}"):
                    task_name = st.text_input(
                        "New Task",
                        placeholder="e.g. Eat 100g protein",
                        key=f"tn_{sid}_{cid}",
                    )
                    one_off = st.checkbox(
                        "One-off task (expires after tonight midnight IST; stays in history once archived)",
                        value=False,
                        key=f"oneoff_{sid}_{cid}",
                    )
                    task_submit = st.form_submit_button("Add Task")

                    if task_submit and task_name.strip():
                        db.create_task(
                            uid,
                            sid,
                            cid,
                            task_name.strip(),
                            repeating=not one_off,
                        )
                        invalidate_habits_bundle()
                        invalidate_dashboard_bundle()
                        st.success("Task added!")
                        st.rerun(scope="fragment")

                for task in tasks:
                    tcol1, tcol2 = st.columns([8, 1])
                    with tcol1:
                        suffix = ""
                        if task.get("repeating", True) is False:
                            suffix = (
                                "<span style='font-size:0.78rem;color:#7A8B95;margin-left:6px'>"
                                "(one-off · until midnight IST)</span>"
                            )
                        st.markdown(
                            f"&nbsp;&nbsp;&nbsp;• {task.get('name','')}{suffix}",
                            unsafe_allow_html=True,
                        )
                    with tcol2:
                        if st.button("✕", key=f"del_task_{sid}_{cid}_{task['id']}"):
                            db.delete_task(uid, sid, cid, task["id"])
                            invalidate_habits_bundle()
                            invalidate_dashboard_bundle()
                            st.rerun(scope="fragment")

                if st.button(f"🗑️ Remove '{cname}'", key=f"del_cat_{sid}_{cid}"):
                    db.delete_category(uid, sid, cid)
                    invalidate_habits_bundle()
                    invalidate_dashboard_bundle()
                    st.success(f"Category '{cname}' deleted.")
                    st.rerun(scope="fragment")

                st.markdown(
                    "<hr style='border-color:#F0F0F0; margin:10px 0;'>",
                    unsafe_allow_html=True,
                )
