"""
ai_planner.py
Generate categories/tasks from Grand Plan using Groq, then apply as create-only ops.
"""

from __future__ import annotations

import json
from typing import Any
import requests

import database as db
from config import get_groq_api_key

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def _safe_json_from_text(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            return {}
    return {}


def generate_structure(grand_plan: str, instruction: str, user_context: dict[str, Any]) -> dict[str, Any]:
    api_key = get_groq_api_key()
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY in environment/secrets.")

    system_prompt = (
        "You are a planning assistant for a habit app. "
        "Return ONLY valid JSON. No markdown. No extra text. "
        "Goal: propose spheres/categories/tasks for next week from the user's plan and instruction. "
        "Never include delete operations. Create-only suggestions.\n\n"
        "Scheduling rules you MUST follow:\n"
        "1) If the plan says 'Alternate Days' with Day A / Day B, you MUST strictly alternate in date order.\n"
        "2) Never assign Day A twice in a row or Day B twice in a row.\n"
        "3) If a phase defines a start date, treat that start date as the first alternation anchor.\n"
        "   - If text says 'Day A: ...' and 'Day B: ...', then phase start date = Day A, next date = Day B, and so on.\n"
        "4) If the user gives an explicit date example (e.g., May 1 is coding from scratch), you MUST preserve it\n"
        "   and continue alternation from that anchor (May 2 becomes the other option).\n"
        "5) For generated tasks for 'next week', output tasks that are consistent with these alternation constraints.\n\n"
        "Schema:\n"
        "{\n"
        '  "spheres": [\n'
        "    {\n"
        '      "name": "string",\n'
        '      "emoji": "string or empty",\n'
        '      "categories": [\n'
        "        {\n"
        '          "name": "string",\n'
        '          "emoji": "string or empty",\n'
        '          "frequency": "daily|weekly",\n'
        '          "tasks": ["string", "..."]\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Keep tasks concise and actionable."
    )

    user_prompt = json.dumps(
        {
            "instruction": instruction,
            "grand_plan": grand_plan,
            "existing": user_context,
        },
        ensure_ascii=False,
    )

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = _safe_json_from_text(content)
    return parsed if isinstance(parsed, dict) else {}


def _norm(s: str) -> str:
    return (s or "").strip().casefold()


def _clean_frequency(freq: str) -> str:
    f = (freq or "daily").strip().lower()
    return f if f in {"daily", "weekly"} else "daily"


def apply_generated_structure(uid: str, generated: dict[str, Any]) -> dict[str, int]:
    summary = {
        "spheres_created": 0,
        "spheres_skipped_missing": 0,
        "categories_created": 0,
        "tasks_created": 0,
        "tasks_skipped_existing": 0,
    }

    existing_spheres = db.get_spheres(uid)
    sphere_by_name = {_norm(s.get("name", "")): s for s in existing_spheres}

    for s in generated.get("spheres", []) if isinstance(generated.get("spheres", []), list) else []:
        sphere_name = (s.get("name") or "").strip()
        if not sphere_name:
            continue
        sphere_emoji = (s.get("emoji") or "").strip()

        sphere = sphere_by_name.get(_norm(sphere_name))
        if not sphere:
            summary["spheres_skipped_missing"] += 1
            continue
        sid = sphere["id"]

        existing_categories = db.get_categories(uid, sid)
        cat_by_name = {_norm(c.get("name", "")): c for c in existing_categories}

        for c in s.get("categories", []) if isinstance(s.get("categories", []), list) else []:
            cat_name = (c.get("name") or "").strip()
            if not cat_name:
                continue
            cat_emoji = (c.get("emoji") or "").strip()
            cat_freq = _clean_frequency(c.get("frequency", "daily"))

            cat = cat_by_name.get(_norm(cat_name))
            if not cat:
                try:
                    cid = db.create_category(uid, sid, cat_name, cat_emoji, frequency=cat_freq)
                except TypeError:
                    cid = db.create_category(uid, sid, cat_name, cat_emoji)
                cat = {"id": cid, "name": cat_name}
                cat_by_name[_norm(cat_name)] = cat
                summary["categories_created"] += 1
            cid = cat["id"]

            existing_tasks = db.get_tasks(uid, sid, cid)
            existing_task_names = {_norm(t.get("name", "")) for t in existing_tasks}
            for task in c.get("tasks", []) if isinstance(c.get("tasks", []), list) else []:
                task_name = (task or "").strip()
                if not task_name:
                    continue
                key = _norm(task_name)
                if key in existing_task_names:
                    summary["tasks_skipped_existing"] += 1
                    continue
                db.create_task(uid, sid, cid, task_name, repeating=True)
                existing_task_names.add(key)
                summary["tasks_created"] += 1

    return summary


def get_creation_preview(uid: str, generated: dict[str, Any]) -> dict[str, Any]:
    """
    Return only the net-new items that would be created (dry-run, no writes).
    """
    preview = {
        "spheres_skipped_missing": [],
        "categories_to_create": [],
        "tasks_to_create": [],
        "counts": {
            "spheres_skipped_missing": 0,
            "categories": 0,
            "tasks": 0,
        },
    }

    existing_spheres = db.get_spheres(uid)
    sphere_by_name = {_norm(s.get("name", "")): s for s in existing_spheres}

    for s in generated.get("spheres", []) if isinstance(generated.get("spheres", []), list) else []:
        sphere_name = (s.get("name") or "").strip()
        if not sphere_name:
            continue
        sphere_emoji = (s.get("emoji") or "").strip()

        existing_sphere = sphere_by_name.get(_norm(sphere_name))
        sphere_exists = existing_sphere is not None
        if not sphere_exists:
            preview["spheres_skipped_missing"].append({"name": sphere_name, "emoji": sphere_emoji})
            preview["counts"]["spheres_skipped_missing"] += 1
            continue

        sid = existing_sphere["id"] if existing_sphere else None
        existing_categories = db.get_categories(uid, sid) if sid else []
        cat_by_name = {_norm(c.get("name", "")): c for c in existing_categories}

        for c in s.get("categories", []) if isinstance(s.get("categories", []), list) else []:
            cat_name = (c.get("name") or "").strip()
            if not cat_name:
                continue
            cat_emoji = (c.get("emoji") or "").strip()
            cat_freq = _clean_frequency(c.get("frequency", "daily"))

            existing_cat = cat_by_name.get(_norm(cat_name))
            cat_exists = existing_cat is not None
            if not cat_exists:
                preview["categories_to_create"].append(
                    {
                        "sphere": sphere_name,
                        "name": cat_name,
                        "emoji": cat_emoji,
                        "frequency": cat_freq,
                    }
                )
                preview["counts"]["categories"] += 1

            cid = existing_cat["id"] if existing_cat else None
            existing_tasks = db.get_tasks(uid, sid, cid) if (sid and cid) else []
            existing_task_names = {_norm(t.get("name", "")) for t in existing_tasks}

            for task in c.get("tasks", []) if isinstance(c.get("tasks", []), list) else []:
                task_name = (task or "").strip()
                if not task_name:
                    continue

                # If sphere/category don't exist yet, every non-empty task is new.
                if not sphere_exists or not cat_exists or _norm(task_name) not in existing_task_names:
                    preview["tasks_to_create"].append(
                        {
                            "sphere": sphere_name,
                            "category": cat_name,
                            "name": task_name,
                        }
                    )
                    preview["counts"]["tasks"] += 1

    return preview
