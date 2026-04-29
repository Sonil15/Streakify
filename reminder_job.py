"""
reminder_job.py
Standalone script run by GitHub Actions at 8:00 PM IST daily.

Logic:
  For every user → for every category:
    If today has ZERO completed tasks AND freeze_count == 0:
      → Send Telegram warning: "You're about to lose your streak!"
    If today has ZERO completed tasks AND freeze_count > 0:
      → Send a softer nudge: "Complete a task or a freeze will be used tonight."
"""

import os
import sys
import json
import requests
from datetime import datetime, date, timedelta
import pytz
from dotenv import load_dotenv

# Allow running from repo root
sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore
from config import get_service_account_dict, get_telegram_token, TIMEZONE

# ---------------------------------------------------------------------------
# Initialise Firebase (standalone, no Streamlit)
# ---------------------------------------------------------------------------

def init_firebase():
    if not firebase_admin._apps:
        sa = get_service_account_dict()
        cred = credentials.Certificate(sa)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------

TELEGRAM_TOKEN = get_telegram_token()
TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send a Telegram message. Returns True on success."""
    if not chat_id or not TELEGRAM_TOKEN:
        print(f"  ⚠ Skipping Telegram: missing chat_id or token.")
        return False
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"  ✗ Telegram error for chat_id={chat_id}: {e}")
        return False


# ---------------------------------------------------------------------------
# Date helpers (IST)
# ---------------------------------------------------------------------------

def today_ist() -> str:
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz).strftime("%Y-%m-%d")


def is_weekend_ist(date_str: str) -> bool:
    d = date.fromisoformat(date_str)
    # Monday=0 ... Sunday=6
    return d.weekday() >= 5


def week_start_str(date_str: str) -> str:
    d = date.fromisoformat(date_str)
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Firestore query helpers
# ---------------------------------------------------------------------------

def get_all_users(fdb) -> list[dict]:
    users = []
    for doc in fdb.collection("users").stream():
        d = doc.to_dict()
        d["uid"] = doc.id
        users.append(d)
    return users


def get_spheres(fdb, uid: str) -> list[dict]:
    docs = fdb.collection("users").document(uid).collection("spheres").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]


def get_categories(fdb, uid: str, sphere_id: str) -> list[dict]:
    docs = (
        fdb.collection("users").document(uid)
        .collection("spheres").document(sphere_id)
        .collection("categories").stream()
    )
    return [{**d.to_dict(), "id": d.id} for d in docs]


def get_today_completion(fdb, uid: str, sphere_id: str, category_id: str, date_str: str) -> list:
    doc = (
        fdb.collection("users").document(uid)
        .collection("spheres").document(sphere_id)
        .collection("categories").document(category_id)
        .collection("completions").document(date_str)
        .get()
    )
    if not doc.exists:
        return []
    return doc.to_dict().get("completed_tasks", [])


def has_completion_in_range(
    fdb,
    uid: str,
    sphere_id: str,
    category_id: str,
    start_date_str: str,
    end_date_str: str,
) -> bool:
    docs = (
        fdb.collection("users").document(uid)
        .collection("spheres").document(sphere_id)
        .collection("categories").document(category_id)
        .collection("completions")
        .where("date", ">=", start_date_str)
        .where("date", "<=", end_date_str)
        .stream()
    )
    for doc in docs:
        if doc.to_dict().get("completed_tasks", []):
            return True
    return False


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def run_reminders():
    print(f"\n{'='*55}")
    print(f"  Streakify Reminder Job — {today_ist()} (IST)")
    print(f"{'='*55}\n")

    fdb      = init_firebase()
    today    = today_ist()
    users    = get_all_users(fdb)
    sent     = 0
    skipped  = 0

    for user in users:
        uid     = user["uid"]
        name    = user.get("display_name", "there")
        tg_id   = user.get("telegram_chat_id", "")
        spheres = get_spheres(fdb, uid)

        print(f"→ User: {name} ({uid})")

        for sphere in spheres:
            sid  = sphere["id"]
            cats = get_categories(fdb, uid, sid)

            for cat in cats:
                cid          = cat["id"]
                cat_name     = cat.get("name", "Unknown Category")
                sphere_name  = sphere.get("name", "")
                streak       = cat.get("streak", 0)
                freeze_count = cat.get("freeze_count", 0)
                frequency    = (cat.get("frequency") or "daily").lower()

                if streak == 0:
                    # No active streak to protect
                    continue

                if frequency == "weekly":
                    if not is_weekend_ist(today):
                        print(f"    ⏭ {sphere_name} › {cat_name}: weekly reminder skipped (weekday)")
                        continue
                    week_start = week_start_str(today)
                    week_end = (date.fromisoformat(week_start) + timedelta(days=6)).strftime("%Y-%m-%d")
                    completed = has_completion_in_range(fdb, uid, sid, cid, week_start, week_end)
                else:
                    completed = bool(get_today_completion(fdb, uid, sid, cid, today))

                if completed:
                    print(
                        f"    ✅ {sphere_name} › {cat_name}: done for "
                        f"{'this week' if frequency == 'weekly' else 'today'}"
                    )
                    continue

                # At risk!
                if freeze_count == 0:
                    # DANGER: streak will reset at midnight
                    msg = (
                        f"🚨 <b>Streakify Alert!</b>\n\n"
                        f"Hey {name}! You haven't completed any tasks in <b>{sphere_name} › {cat_name}</b> "
                        f"{'this week' if frequency == 'weekly' else 'today'}.\n\n"
                        f"⚠️ You have <b>0 freezes left</b> — your "
                        f"<b>{streak}-{'week' if frequency == 'weekly' else 'day'} streak</b> "
                        f"will reset at midnight tonight!\n\n"
                        f"Quick, go log a task now! 💪"
                    )
                    print(f"    🚨 DANGER — {sphere_name} › {cat_name} (streak={streak}, freezes=0)")
                else:
                    # Will auto-use a freeze, but worth a nudge
                    msg = (
                        f"⏰ <b>Streakify Reminder!</b>\n\n"
                        f"Hey {name}! Nothing logged yet in <b>{sphere_name} › {cat_name}</b> "
                        f"{'this week' if frequency == 'weekly' else 'today'}.\n\n"
                        f"❄️ A freeze will be used automatically tonight "
                        f"(you have {freeze_count} left).\n\n"
                        f"But why waste a freeze? Smash a task now! 🔥"
                    )
                    print(f"    ⏰ NUDGE — {sphere_name} › {cat_name} (streak={streak}, freezes={freeze_count})")

                ok = send_telegram_message(tg_id, msg)
                if ok:
                    sent += 1
                    print(f"       → Telegram sent ✓")
                else:
                    skipped += 1

    print(f"\n{'='*55}")
    print(f"  Done. Sent: {sent} | Skipped: {skipped}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    run_reminders()
