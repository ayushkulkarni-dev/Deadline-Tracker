import json

from database import get_deadlines, get_setting, email_was_sent, mark_email_sent
from utils import reminder_needed, days_left
from notifier import send_deadline_email


def get_pending_email_reminders(offsets):
    """One email per deadline: the most urgent offset that hasn't been emailed yet."""
    pending = []
    for d in get_deadlines():
        needed = sorted(n for n in offsets if reminder_needed(d["date"], n))
        if not needed:
            continue

        urgent = needed[0]
        if email_was_sent(d["id"], urgent, d["date"]):
            continue

        pending.append({
            "deadline_id": d["id"],
            "title": d["title"],
            "subject": d["subject"] or "",
            "date": d["date"],
            "covers": needed,
        })
    return pending


def send_pending_emails():
    """Returns (sent_count, errors). Marks as sent ONLY when the email succeeded."""
    offsets = json.loads(get_setting("reminder_offsets", "[1]"))
    receiver = get_setting("receiver_email") or None     # saved value, .env is the fallback

    sent, errors = 0, []
    for r in get_pending_email_reminders(offsets):
        ok, message = send_deadline_email(
            title=r["title"],
            subject=r["subject"],
            due_date=r["date"],
            days_remaining=days_left(r["date"]),
            receiver=receiver,
        )
        if ok:
            for n in r["covers"]:                         # also covers the older offsets
                mark_email_sent(r["deadline_id"], n, r["date"])
            sent += 1
        else:
            errors.append(f"{r['title']}: {message}")
            if "Login failed" in message or "settings missing" in message:
                break                                     # same error for every email, stop early
    return sent, errors