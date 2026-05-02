"""
expire_one_off_tasks_job.py
Scheduled job (GitHub Actions): archive one-off tasks after their IST day ends.

Non-repeating tasks stay in Firestore under tasks/{taskId} with archived=True
(completions history unchanged). Active lists use get_tasks(), which hides them.
"""

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

import database as db


def run_expire_one_off_tasks():
    today = db.today_ist()
    print(f"\n{'='*55}")
    print(f"  Expire one-off tasks — {today} (IST)")
    print(f"{'='*55}\n")

    users = db.get_all_users()
    total_archived = 0

    for user in users:
        uid = user["uid"]
        name = user.get("display_name", uid[:8])
        n = db.expire_one_off_tasks_for_user(uid)
        if n:
            print(f"  ✓ {name}: archived {n} one-off task(s)")
        total_archived += n

    print(f"\n  Done. Total archived this run: {total_archived}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    run_expire_one_off_tasks()
