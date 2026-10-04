import streamlit as st

from database import get_deadlines, was_sent, mark_sent
from utils import reminder_needed, days_left, days_label


def get_pending_reminders(offsets):
    """Return one reminder per deadline: the most urgent offset that hasn't been sent."""
    pending = []
    for d in get_deadlines():
        # offsets (e.g. 7, 2, 1) whose reminder window has started
        needed = sorted(n for n in offsets if reminder_needed(d["date"], n))
        if not needed:
            continue

        urgent = needed[0]                       # smallest = closest to the deadline
        if was_sent(d["id"], urgent, d["date"]):
            continue                             # already handled, no duplicate

        pending.append({
            "deadline_id": d["id"],
            "title": d["title"],
            "subject": d["subject"] or "",
            "date": d["date"],
            "days_before": urgent,
            "covers": needed,                    # all offsets this reminder replaces
        })
    return sorted(pending, key=lambda r: r["date"])


def dismiss_reminder(reminder):
    """Mark every covered offset as sent, so the older ones don't pop up later."""
    for n in reminder["covers"]:
        mark_sent(reminder["deadline_id"], n, reminder["date"])


def render_reminders(offsets):
    pending = get_pending_reminders(offsets)
    if not pending:
        return

    st.subheader(f"⏰ Reminders ({len(pending)})")
    for r in pending:
        c1, c2 = st.columns([5, 1])
        label = days_label(days_left(r["date"]))
        c1.warning(f"**{r['title']}** ({r['subject']}) — {label} · {r['date']}")
        if c2.button("Dismiss", key=f"dismiss_{r['deadline_id']}_{r['days_before']}"):
            dismiss_reminder(r)
            st.rerun()
    st.divider()