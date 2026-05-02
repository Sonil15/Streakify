"""
Build Habits tab data in parallel (categories + tasks) to reduce latency.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import database as db


def build_habits_bundle(uid: str) -> dict[str, Any]:
    spheres = db.get_spheres(uid)
    if not spheres:
        return {"uid": uid, "spheres": []}

    sphere_rows = []
    for sp in spheres:
        sid = sp["id"]
        sphere_rows.append((sp, db.get_categories(uid, sid)))

    work: list[tuple[int, str, dict]] = []
    idx = 0
    for sp, cats in sphere_rows:
        for cat in cats:
            work.append((idx, sp["id"], dict(cat)))
            idx += 1

    tasks_by_cat: dict[str, list[dict]] = {}
    if work:
        max_workers = min(16, max(4, len(work)))

        def _load_tasks(row: tuple[int, str, dict]) -> tuple[int, str, list[dict]]:
            i, sid, cat = row
            cid = cat["id"]
            return i, f"{sid}:{cid}", db.get_tasks(uid, sid, cid)

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = [ex.submit(_load_tasks, row) for row in work]
            loaded = [f.result() for f in as_completed(futs)]
        loaded.sort(key=lambda x: x[0])
        for _, key, tasks in loaded:
            tasks_by_cat[key] = tasks

    spheres_out = []
    for sp, cats in sphere_rows:
        sid = sp["id"]
        c_out = []
        for cat in cats:
            cid = cat["id"]
            c = dict(cat)
            c["tasks"] = tasks_by_cat.get(f"{sid}:{cid}", [])
            c_out.append(c)
        spheres_out.append({"sphere": sp, "categories": c_out})

    return {"uid": uid, "spheres": spheres_out}
