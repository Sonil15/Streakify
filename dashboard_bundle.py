"""
Build dashboard data in parallel to avoid sequential Firestore latency (main UX bottleneck).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import database as db
import streak_logic as sl


def build_dashboard_bundle(uid: str, today: str) -> dict[str, Any]:
    """
    One sequential pass to list spheres/categories, then parallel fetch per category:
    tasks + today's completion + reconcile_streak.
    """
    spheres = db.get_spheres(uid)
    indexed_work: list[tuple[int, dict, dict]] = []
    i = 0
    for sp in spheres:
        sid = sp["id"]
        for cat in db.get_categories(uid, sid):
            indexed_work.append((i, sp, dict(cat)))
            i += 1

    if not indexed_work:

        return {
            "uid": uid,
            "today": today,
            "spheres": spheres,
            "items": [],
            "by_sphere": {},
        }

    max_workers = min(16, max(4, len(indexed_work)))

    def _one(row: tuple[int, dict, dict]) -> tuple[int, dict[str, Any]]:
        idx, sp, cat = row
        sid, cid = sp["id"], cat["id"]
        tasks = db.get_tasks(uid, sid, cid)
        comp = db.get_completion(uid, sid, cid, today)
        cat_rec = sl.reconcile_streak(uid, sid, cat)
        item = {
            "sphere": sp,
            "cat": cat_rec,
            "tasks": tasks,
            "completion_doc": comp,
        }
        return idx, item

    results: list[tuple[int, dict[str, Any]]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_one, row) for row in indexed_work]
        for f in as_completed(futs):
            results.append(f.result())

    results.sort(key=lambda x: x[0])
    items = [it for _, it in results]

    by_sphere: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        sid = it["sphere"]["id"]
        by_sphere.setdefault(sid, []).append(it)

    return {
        "uid": uid,
        "today": today,
        "spheres": spheres,
        "items": items,
        "by_sphere": by_sphere,
    }
