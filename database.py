"""
database.py
All Firestore read/write operations via firebase-admin SDK.

Firestore hierarchy:
  users/{uid}
    .spheres/{sphereId}
      .categories/{categoryId}
        .tasks/{taskId}
        .completions/{YYYY-MM-DD}   ← which task IDs were ticked that day
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date, timedelta
import streamlit as st
from config import get_service_account_dict, TIMEZONE
import pytz

_IST = pytz.timezone(TIMEZONE)


# ---------------------------------------------------------------------------
# Initialisation (cached across Streamlit reruns)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _init_firestore():
    if not firebase_admin._apps:
        sa = get_service_account_dict()
        cred = credentials.Certificate(sa)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def get_db():
    return _init_firestore()


def today_ist() -> str:
    """Return today's date string in IST (YYYY-MM-DD)."""
    return datetime.now(_IST).strftime("%Y-%m-%d")


def now_ist() -> datetime:
    return datetime.now(_IST)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def create_user_profile(uid: str, data: dict):
    get_db().collection("users").document(uid).set({
        **data,
        "created_at": firestore.SERVER_TIMESTAMP,
    })


def get_user_profile(uid: str) -> dict | None:
    doc = get_db().collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def update_user_profile(uid: str, data: dict):
    get_db().collection("users").document(uid).update(data)


def find_user_by_email(email: str) -> dict | None:
    """Return the user profile dict (with added 'uid' key) for the given email."""
    docs = get_db().collection("users").where("email", "==", email).limit(1).stream()
    for doc in docs:
        d = doc.to_dict()
        d["uid"] = doc.id
        return d
    return None


def get_all_users() -> list[dict]:
    """Used by the reminder job to iterate over every user."""
    users = []
    for doc in get_db().collection("users").stream():
        d = doc.to_dict()
        d["uid"] = doc.id
        users.append(d)
    return users


# ---------------------------------------------------------------------------
# Spheres
# ---------------------------------------------------------------------------

def _spheres_ref(uid: str):
    return get_db().collection("users").document(uid).collection("spheres")


def get_spheres(uid: str) -> list[dict]:
    docs = _spheres_ref(uid).order_by("created_at").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        result.append(d)
    return result


def create_sphere(uid: str, name: str, emoji: str) -> str:
    ref = _spheres_ref(uid).document()
    ref.set({
        "name":       name,
        "emoji":      emoji,
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return ref.id


def update_sphere(uid: str, sphere_id: str, data: dict):
    _spheres_ref(uid).document(sphere_id).update(data)


def delete_sphere(uid: str, sphere_id: str):
    """Delete sphere + all nested subcollections."""
    _delete_collection(
        _spheres_ref(uid).document(sphere_id).collection("categories")
    )
    _spheres_ref(uid).document(sphere_id).delete()


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def _cats_ref(uid: str, sphere_id: str):
    return (
        get_db()
        .collection("users").document(uid)
        .collection("spheres").document(sphere_id)
        .collection("categories")
    )


def get_categories(uid: str, sphere_id: str) -> list[dict]:
    docs = _cats_ref(uid, sphere_id).order_by("created_at").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        result.append(d)
    return result


def create_category(uid: str, sphere_id: str, name: str, emoji: str) -> str:
    ref = _cats_ref(uid, sphere_id).document()
    ref.set({
        "name":                     name,
        "emoji":                    emoji,
        "streak":                   0,
        "freeze_count":             0,
        "consecutive_days":         0,   # days towards next freeze
        "last_completed_date":      None,
        "created_at":               firestore.SERVER_TIMESTAMP,
    })
    return ref.id


def get_category(uid: str, sphere_id: str, category_id: str) -> dict | None:
    doc = _cats_ref(uid, sphere_id).document(category_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    d["id"] = doc.id
    return d


def update_category(uid: str, sphere_id: str, category_id: str, data: dict):
    _cats_ref(uid, sphere_id).document(category_id).update(data)


def delete_category(uid: str, sphere_id: str, category_id: str):
    cat_ref = _cats_ref(uid, sphere_id).document(category_id)
    _delete_collection(cat_ref.collection("tasks"))
    _delete_collection(cat_ref.collection("completions"))
    cat_ref.delete()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def _tasks_ref(uid: str, sphere_id: str, category_id: str):
    return _cats_ref(uid, sphere_id).document(category_id).collection("tasks")


def get_tasks(uid: str, sphere_id: str, category_id: str) -> list[dict]:
    docs = _tasks_ref(uid, sphere_id, category_id).order_by("created_at").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        result.append(d)
    return result


def create_task(uid: str, sphere_id: str, category_id: str, name: str) -> str:
    ref = _tasks_ref(uid, sphere_id, category_id).document()
    ref.set({
        "name":       name,
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return ref.id


def delete_task(uid: str, sphere_id: str, category_id: str, task_id: str):
    _tasks_ref(uid, sphere_id, category_id).document(task_id).delete()


# ---------------------------------------------------------------------------
# Daily Completions
# ---------------------------------------------------------------------------

def _completions_ref(uid: str, sphere_id: str, category_id: str):
    return _cats_ref(uid, sphere_id).document(category_id).collection("completions")


def get_completion(uid: str, sphere_id: str, category_id: str, date_str: str) -> dict:
    """Return the completion doc for a specific date, or empty dict."""
    doc = _completions_ref(uid, sphere_id, category_id).document(date_str).get()
    return doc.to_dict() if doc.exists else {}


def set_task_completion(
    uid: str,
    sphere_id: str,
    category_id: str,
    task_id: str,
    date_str: str,
    completed: bool,
):
    """
    Mark or unmark a single task as done for a given date.
    Uses Firestore array_union / array_remove so concurrent updates are safe.
    """
    ref = _completions_ref(uid, sphere_id, category_id).document(date_str)
    if completed:
        ref.set(
            {
                "completed_tasks": firestore.ArrayUnion([task_id]),
                "date":            date_str,
                "updated_at":      firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
    else:
        ref.set(
            {
                "completed_tasks": firestore.ArrayRemove([task_id]),
                "date":            date_str,
                "updated_at":      firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )


def get_completion_history(
    uid: str,
    sphere_id: str,
    category_id: str,
    days: int = 365,
) -> dict[str, bool]:
    """
    Return {date_str: had_at_least_one_completion} for the last `days` days.
    """
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    docs = (
        _completions_ref(uid, sphere_id, category_id)
        .where("date", ">=", cutoff)
        .stream()
    )
    history: dict[str, bool] = {}
    for doc in docs:
        d = doc.to_dict()
        tasks_done = d.get("completed_tasks", [])
        history[doc.id] = len(tasks_done) > 0
    return history


def get_all_categories_for_user(uid: str) -> list[dict]:
    """
    Flatten all categories across all spheres for a user.
    Each dict has sphere_id + category data.
    Used by the reminder job.
    """
    result = []
    for sphere in get_spheres(uid):
        for cat in get_categories(uid, sphere["id"]):
            cat["sphere_id"] = sphere["id"]
            cat["sphere_name"] = sphere["name"]
            result.append(cat)
    return result


# ---------------------------------------------------------------------------
# Helper: delete a Firestore collection in batches
# ---------------------------------------------------------------------------

def _delete_collection(col_ref, batch_size: int = 50):
    docs = col_ref.limit(batch_size).stream()
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted += 1
    if deleted >= batch_size:
        _delete_collection(col_ref, batch_size)
