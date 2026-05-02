"""
Dashboard: cached parallel Firestore bundle + per-category fragments.

Checkbox interactions only rerun the touched category fragment (not the whole app).
Scoreboard uses a lightweight fragment with run_every to pick up session overlays quickly.

Without this, every toggle sequentially hit Firestore for every category (multi-second lag).
"""

from __future__ import annotations

import queue
import threading
from datetime import timedelta
from typing import Any

import streamlit as st

import database as db
import streak_logic as sl
import ui_components as ui
from dashboard_bundle import (
    STRUCTURE_BUNDLE_KEY,
    ensure_structure_bundle,
    invalidate_dashboard_bundle,
)

_result_queue: queue.Queue = queue.Queue()
_cat_locks: dict[str, threading.Lock] = {}


def dash_cb_key(uid: str, today: str, sid: str, cid: str, tid: str) -> str:
    return f"dash_cb_{today}_{uid}_{sid}_{cid}_{tid}"


def dash_cat_key(sid: str, cid: str) -> str:
    return f"dash_cat_{sid}_{cid}"


def _lock_for_category(sid: str, cid: str) -> threading.Lock:
    key = f"{sid}:{cid}"
    if key not in _cat_locks:
        _cat_locks[key] = threading.Lock()
    return _cat_locks[key]


def _drain_result_queue() -> list[tuple]:
    out: list[tuple] = []
    while True:
        try:
            out.append(_result_queue.get_nowait())
        except queue.Empty:
            break
    return out


def _sync_day_anchor(today: str) -> None:
    anchor = st.session_state.get("dash_anchor_day")
    if anchor == today:
        return
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and (
            k.startswith("dash_cb_") or k.startswith("dash_cat_")
        ):
            del st.session_state[k]
    st.session_state["dash_anchor_day"] = today
    invalidate_dashboard_bundle()


def _get_item(bundle: dict, sid: str, cid: str) -> dict[str, Any] | None:
    for it in bundle.get("items", []):
        if it["sphere"]["id"] == sid and it["cat"]["id"] == cid:
            return it
    return None


def _patch_bundle_item(
    uid: str, today: str, sid: str, cid: str, cat_row: dict
) -> None:
    b = st.session_state.get(STRUCTURE_BUNDLE_KEY)
    if not b:
        return
    for it in b.get("items", []):
        if it["sphere"]["id"] == sid and it["cat"]["id"] == cid:
            it["cat"] = dict(cat_row)
            tids = [t["id"] for t in it["tasks"]]
            done = [
                tid
                for tid in tids
                if st.session_state.get(
                    dash_cb_key(uid, today, sid, cid, tid), False
                )
            ]
            it["completion_doc"] = {"completed_tasks": done, "date": today}
            break


def _apply_optimistic_cat(
    cat_state_key: str,
    desired: bool,
    remaining: list[str],
    cat_before: dict,
) -> None:
    if desired:
        st.session_state[cat_state_key] = sl.compute_record_completion_for_today(
            cat_before
        )
        return
    if remaining:
        st.session_state[cat_state_key] = cat_before
        return
    freq = (cat_before.get("frequency") or "daily").lower()
    if freq == "daily":
        st.session_state[cat_state_key] = sl.compute_daily_uncheck_rollback(
            cat_before
        )


def _persist_job(
    uid: str,
    sid: str,
    cid: str,
    tid: str,
    today: str,
    desired: bool,
    remaining: list[str],
    rollback_checkbox: bool,
) -> None:
    lk = _lock_for_category(sid, cid)
    with lk:
        try:
            row = db.get_category(uid, sid, cid)
            if row is None:
                raise RuntimeError("Category not found")
            cat = sl.reconcile_streak(uid, sid, row)
            db.set_task_completion(uid, sid, cid, tid, today, desired)
            if desired:
                cat = sl.record_completion_for_today(uid, sid, cat)
            else:
                cat = sl.check_if_still_active_today(uid, sid, cid, remaining, cat)
            freeze = bool(cat.get("freeze_awarded_today"))
            _result_queue.put(("ok", sid, cid, dict(cat), freeze, bool(desired)))
        except Exception as e:
            _result_queue.put(("err", sid, cid, tid, rollback_checkbox, str(e)))


def make_toggle_cb(
    uid: str,
    today: str,
    sid: str,
    cid: str,
    tid: str,
    task_ids: tuple[str, ...],
    cat_state_key: str,
):
    def _cb() -> None:
        desired = bool(st.session_state[dash_cb_key(uid, today, sid, cid, tid)])
        rollback_checkbox = not desired

        cat_before = dict(st.session_state[cat_state_key])
        remaining = [
            x
            for x in task_ids
            if st.session_state.get(dash_cb_key(uid, today, sid, cid, x), False)
        ]

        _apply_optimistic_cat(cat_state_key, desired, remaining, cat_before)

        threading.Thread(
            target=_persist_job,
            args=(
                uid,
                sid,
                cid,
                tid,
                today,
                desired,
                remaining,
                rollback_checkbox,
            ),
            daemon=True,
        ).start()

    return _cb


def _process_drain(uid: str, today: str, events: list[tuple]) -> None:
    celebrate = False
    for ev in events:
        if ev[0] == "ok":
            _, sid, cid, cat_row, freeze_aw, did_check = ev
            st.session_state[dash_cat_key(sid, cid)] = cat_row
            _patch_bundle_item(uid, today, sid, cid, cat_row)
            if did_check:
                celebrate = True
            if freeze_aw:
                st.success(
                    f"🎉 You earned a new ❄️ Freeze for **{cat_row.get('name', 'this category')}**! "
                    f"You now have {cat_row.get('freeze_count', 0)} freezes."
                )
        elif ev[0] == "err":
            _, sid, cid, tid, rollback_checkbox, msg = ev
            cb_key = dash_cb_key(uid, today, sid, cid, tid)
            st.session_state[cb_key] = rollback_checkbox
            st.toast(f"Could not save your change: {msg}", icon="⚠️")
    if celebrate:
        st.balloons()


@st.fragment
def _category_row_fragment(uid: str, today: str, item: dict[str, Any]) -> None:
    """Only this category reruns when its checkboxes change."""
    drained = _drain_result_queue()
    if drained:
        _process_drain(uid, today, drained)

    bundle = ensure_structure_bundle(uid, today)
    sid = item["sphere"]["id"]
    cid = item["cat"]["id"]
    fresh = _get_item(bundle, sid, cid)
    if fresh is not None:
        item = fresh

    cat = item["cat"]
    tasks = item["tasks"]
    sphere = item["sphere"]
    cat_title = f"{cat.get('emoji','')} {cat.get('name','')}".strip()
    frequency = (cat.get("frequency") or "daily").lower()
    cadence_label = "week" if frequency == "weekly" else "day"

    ck = dash_cat_key(sid, cid)
    if ck not in st.session_state:
        st.session_state[ck] = dict(cat)

    completion_doc = item.get("completion_doc") or {}
    completed_ids = db.completion_ids_for_active_tasks(
        list(completion_doc.get("completed_tasks", [])),
        tasks,
    )

    task_ids = tuple(t["id"] for t in tasks)
    for task in tasks:
        tid = task["id"]
        cb_k = dash_cb_key(uid, today, sid, cid, tid)
        if cb_k not in st.session_state:
            st.session_state[cb_k] = tid in completed_ids

    cat_display = st.session_state[ck]

    if tasks:
        for task in tasks:
            tid = task["id"]
            cb_k = dash_cb_key(uid, today, sid, cid, tid)
            st.checkbox(
                task.get("name", ""),
                key=cb_k,
                on_change=make_toggle_cb(uid, today, sid, cid, tid, task_ids, ck),
            )

    is_done_today = any(
        st.session_state.get(dash_cb_key(uid, today, sid, cid, t["id"]), False)
        for t in tasks
    )

    with st.expander(
        f"{cat_title} — "
        f"{sl.streak_emoji(cat_display.get('streak', 0))} "
        f"**{cat_display.get('streak', 0)} {cadence_label} streak**",
        expanded=not is_done_today,
    ):
        if not tasks:
            st.caption("No tasks yet — add some in the Habits tab!")
            return

        done_ct = sum(
            1
            for t in tasks
            if st.session_state.get(
                dash_cb_key(uid, today, sid, cid, t["id"]), False
            )
        )
        pct = done_ct / len(tasks) if tasks else 0
        st.progress(pct, text=f"{done_ct}/{len(tasks)} tasks done today")


@st.fragment(run_every=timedelta(seconds=0.25))
def _scoreboard_fragment(uid: str, today: str) -> None:
    """Polls so streak cards catch session overlays without rerunning every category."""
    drained = _drain_result_queue()
    if drained:
        _process_drain(uid, today, drained)

    bundle = st.session_state.get(STRUCTURE_BUNDLE_KEY)
    if not bundle or bundle.get("uid") != uid or bundle.get("today") != today:
        return

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### 🏆 Streak Scoreboard", unsafe_allow_html=True)

    all_cats_flat: list[dict] = []
    for it in bundle.get("items", []):
        c = dict(it["cat"])
        sid = it["sphere"]["id"]
        c["sphere_name"] = it["sphere"].get("name", "")
        c["sphere_emoji"] = it["sphere"].get("emoji", "")
        ov = st.session_state.get(dash_cat_key(sid, c["id"]))
        if ov is not None:
            for field in (
                "streak",
                "freeze_count",
                "consecutive_days",
                "last_completed_date",
            ):
                if field in ov:
                    c[field] = ov[field]
        all_cats_flat.append(c)

    if all_cats_flat:
        all_cats_flat.sort(key=lambda c: c.get("streak", 0), reverse=True)
        cols = st.columns(min(len(all_cats_flat), 3))
        for idx, cat in enumerate(all_cats_flat):
            with cols[idx % 3]:
                ui.render_streak_card(cat)


def render_dashboard_tasks_and_scoreboard(uid: str, _dname: str, today: str) -> None:
    """
    Shell: builds/refreshes bundle once per full run; per-category fragments handle toggles.
    """
    _sync_day_anchor(today)
    bundle = ensure_structure_bundle(uid, today)

    st.markdown("### Today's Tasks", unsafe_allow_html=True)
    st.caption("Check off at least one task per category to keep your streak alive!")

    if not bundle["spheres"]:
        st.info(
            "🌱 You haven't created any Spheres yet! "
            "Head to the **📋 Habits** tab to get started."
        )
        return

    for sphere in bundle["spheres"]:
        sid = sphere["id"]
        sphere_title = f"{sphere.get('emoji','')} {sphere.get('name','')}".strip()
        st.markdown(
            f"<div class='section-header'>{sphere_title}</div>",
            unsafe_allow_html=True,
        )
        for item in bundle.get("by_sphere", {}).get(sid, []):
            _category_row_fragment(uid, today, item)

    _scoreboard_fragment(uid, today)
