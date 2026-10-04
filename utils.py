from datetime import date, datetime, timedelta


def days_left(date_str):
    """'2026-10-10' -> number of days from today (negative = overdue)."""
    due = datetime.strptime(date_str, "%Y-%m-%d").date()
    return (due - date.today()).days


def categorize(days):
    if days < 0:
        return "Overdue"
    if days == 0:
        return "Due today"
    if days == 1:
        return "Tomorrow"
    if days <= 7:
        return "This Week"
    return "Upcoming"


def days_label(days):
    if days < 0:
        n = -days
        return f"{n} day{'s' if n != 1 else ''} overdue"
    if days == 0:
        return "Due today"
    if days == 1:
        return "Due tomorrow"
    return f"{days} days left"

def reminder_date(date_str, days_before):
    due = datetime.strptime(date_str, "%Y-%m-%d").date()
    return due - timedelta(days=days_before)

def reminder_needed(date_str, days_before, today=None):
    today = today or date.today()
    due = datetime.strptime(date_str, "%Y-%m-%d").date()
    return reminder_date(date_str, days_before) <= today <= due

import re

def is_valid_email(address):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", address.strip()))