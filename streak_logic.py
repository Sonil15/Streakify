"""
streak_logic.py
All streak and freeze mechanics live here.

Rules:
- Streak is at the CATEGORY level.
- A day "counts" if at least 1 task in the category was completed.
- Every 7 consecutive completed days → earn 1 Freeze for that category.
- If a day ends with 0 completions:
    → auto-deduct 1 Freeze to protect streak (if available)
    → otherwise reset streak to 0
- Missed days are reconciled when the user opens the app.
"""

from datetime import date, timedelta
from config import FREEZE_EARN_INTERVAL
import database as db


def _frequency(category: dict) -> str:
    freq = (category.get("frequency") or "daily").lower()
    return freq if freq in {"daily", "weekly"} else "daily"


def _week_start(d: date) -> date:
    """Return Monday of the week containing `d`."""
    return d - timedelta(days=d.weekday())


# ---------------------------------------------------------------------------
# Public: reconcile a category's streak against today's date
# ---------------------------------------------------------------------------

def reconcile_streak(uid: str, sphere_id: str, category: dict) -> dict:
    """
    Compare the category's last_completed_date to today.
    Apply freeze deductions or streak resets for any missed days.
    Writes updates to Firestore and returns the updated category dict.
    """
    category_id = category["id"]
    today_str   = db.today_ist()
    today       = date.fromisoformat(today_str)

    last_str  = category.get("last_completed_date")
    streak    = category.get("streak", 0)
    freezes   = category.get("freeze_count", 0)
    consec    = category.get("consecutive_days", 0)
    frequency = _frequency(category)

    if last_str is None:
        # Brand-new category, nothing to reconcile.
        return category

    last_date = date.fromisoformat(last_str)
    if frequency == "weekly":
        periods_since = (_week_start(today) - _week_start(last_date)).days // 7
        # 0 = same week, 1 = previous week; both are safe
        if periods_since <= 1:
            return category
        missed = periods_since - 1
        # Weekly categories do not use freezes.
        if missed > 0:
            updates = {
                "streak": 0,
                "consecutive_days": 0,
                "freeze_count": 0,
            }
            db.update_category(uid, sphere_id, category_id, updates)
            category.update(updates)
            return category
    else:
        # How many full days have passed since last completion (excluding today)?
        days_since = (today - last_date).days   # e.g. 0 = same day, 1 = yesterday
        # Nothing missed: last activity was today or yesterday
        if days_since <= 1:
            return category
        # days_since >= 2 means at least one day was missed.
        # "missed days" = days_since - 1  (we don't count today yet)
        missed = days_since - 1

    updates: dict = {}

    for _ in range(missed):
        if freezes > 0:
            freezes -= 1
        else:
            streak   = 0
            consec   = 0

    updates["streak"]      = streak
    updates["freeze_count"] = freezes
    updates["consecutive_days"] = consec

    db.update_category(uid, sphere_id, category_id, updates)
    category.update(updates)
    return category


# ---------------------------------------------------------------------------
# Public: call after a task is checked off for today
# ---------------------------------------------------------------------------

def record_completion_for_today(uid: str, sphere_id: str, category: dict) -> dict:
    """
    Called when at least one task is now completed for today.
    Extends the streak, possibly awards a freeze, and updates Firestore.
    Returns the updated category dict.
    """
    category_id = category["id"]
    today_str   = db.today_ist()
    today       = date.fromisoformat(today_str)

    last_str = category.get("last_completed_date")
    streak   = category.get("streak", 0)
    freezes  = category.get("freeze_count", 0)
    consec   = category.get("consecutive_days", 0)
    frequency = _frequency(category)

    if frequency == "weekly":
        if last_str:
            last_date = date.fromisoformat(last_str)
            if _week_start(last_date) == _week_start(today):
                return category  # already recorded this week

        previous_week_start = _week_start(today) - timedelta(days=7)
        if last_str and _week_start(date.fromisoformat(last_str)) == previous_week_start:
            streak += 1
            consec += 1
        else:
            streak = streak + 1 if streak > 0 else 1
            consec = 1
    else:
        # Already recorded today
        if last_str == today_str:
            return category

        yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

        if last_str == yesterday_str:
            # Perfect consecutive day
            streak += 1
            consec += 1
        else:
            # Coming back after a gap (penalisation already applied by reconcile_streak).
            # If streak survived via freezes, increment it; otherwise start from 1.
            streak = streak + 1 if streak > 0 else 1
            consec = 1   # restart the freeze-earning counter after any gap

    # Award freeze every FREEZE_EARN_INTERVAL consecutive days (daily only)
    freeze_awarded = False
    if frequency == "daily" and consec > 0 and consec % FREEZE_EARN_INTERVAL == 0:
        freezes += 1
        freeze_awarded = True

    updates = {
        "streak":               streak,
        "freeze_count":         freezes,
        "consecutive_days":     consec,
        "last_completed_date":  today_str,
    }
    db.update_category(uid, sphere_id, category_id, updates)
    category.update(updates)
    category["freeze_awarded_today"] = freeze_awarded
    return category


# ---------------------------------------------------------------------------
# Public: call after a task is UN-checked (to potentially roll back today)
# ---------------------------------------------------------------------------

def check_if_still_active_today(
    uid: str,
    sphere_id: str,
    category_id: str,
    remaining_completed_task_ids: list,
    category: dict,
) -> dict:
    """
    If the user unchecks all tasks for today, roll back the streak extension
    that was recorded for today.
    """
    if remaining_completed_task_ids:
        # Still at least 1 task done today – streak is intact
        return category

    today_str = db.today_ist()
    if category.get("last_completed_date") != today_str:
        return category  # today wasn't recorded yet, nothing to roll back

    frequency = _frequency(category)
    if frequency == "weekly":
        today = date.fromisoformat(today_str)
        week_start = _week_start(today)
        week_end = week_start + timedelta(days=6)
        still_active_this_week = db.has_completion_in_range(
            uid,
            sphere_id,
            category_id,
            week_start.strftime("%Y-%m-%d"),
            week_end.strftime("%Y-%m-%d"),
        )
        if still_active_this_week:
            return category

        streak = max(0, category.get("streak", 1) - 1)
        consec = max(0, category.get("consecutive_days", 1) - 1)

        previous_period_date = week_start - timedelta(days=1)
        new_last = previous_period_date.strftime("%Y-%m-%d") if streak > 0 else None
        updates = {
            "streak":               streak,
            "freeze_count":         0,
            "consecutive_days":     consec,
            "last_completed_date":  new_last,
        }
        db.update_category(uid, sphere_id, category_id, updates)
        category.update(updates)
        return category

    # Reverse today's streak extension
    today  = date.fromisoformat(today_str)
    streak = max(0, category.get("streak", 1) - 1)
    consec = max(0, category.get("consecutive_days", 1) - 1)

    # Check if we need to revoke a freeze that was awarded today
    freezes = category.get("freeze_count", 0)
    if (consec + 1) % FREEZE_EARN_INTERVAL == 0:
        # A freeze was awarded when consec hit the interval; revoke it
        freezes = max(0, freezes - 1)

    # Restore last_completed_date to yesterday (if streak still > 0)
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    new_last = yesterday_str if streak > 0 else None

    updates = {
        "streak":               streak,
        "freeze_count":         freezes,
        "consecutive_days":     consec,
        "last_completed_date":  new_last,
    }
    db.update_category(uid, sphere_id, category_id, updates)
    category.update(updates)
    return category


# ---------------------------------------------------------------------------
# Helpers for the UI
# ---------------------------------------------------------------------------

def streak_emoji(streak: int) -> str:
    """Return an emoji that scales with streak length."""
    if streak == 0:
        return "💤"
    if streak < 3:
        return "🌱"
    if streak < 7:
        return "🔥"
    if streak < 30:
        return "⚡"
    if streak < 100:
        return "🌟"
    return "🏆"


def streak_color(streak: int) -> str:
    """Return a CSS hex color that gets warmer with a longer streak."""
    if streak == 0:
        return "#B0BEC5"
    if streak < 3:
        return "#81C784"
    if streak < 7:
        return "#FFD54F"
    if streak < 30:
        return "#FF8A65"
    return "#EF5350"


def freeze_display(count: int) -> str:
    """Return e.g. '❄️ x 3' for the given freeze count."""
    if count == 0:
        return "No freezes"
    return "❄️ x " + str(count)


def days_until_next_freeze(consecutive_days: int) -> int:
    remaining = FREEZE_EARN_INTERVAL - (consecutive_days % FREEZE_EARN_INTERVAL)
    return remaining if remaining < FREEZE_EARN_INTERVAL else FREEZE_EARN_INTERVAL
