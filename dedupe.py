import re
from datetime import datetime
from difflib import SequenceMatcher

THRESHOLD = 0.85   # how similar two titles must be (0 to 1) to count as the same deadline


def _text(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _date(value):
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date().isoformat()
    except (ValueError, TypeError):
        return ""


def _similar(a, b):
    if a == b:
        return True
    if re.findall(r"\d+", a) != re.findall(r"\d+", b):
        return False          # "Assignment 1" and "Assignment 2" are different deadlines
    return SequenceMatcher(None, a, b).ratio() >= THRESHOLD


def is_duplicate(a, b):
    """Same date + similar title (+ similar subject if both have one). Time is ignored."""
    if _date(a.get("date")) != _date(b.get("date")):
        return False
    if not _similar(_text(a.get("title")), _text(b.get("title"))):
        return False
    subject_a, subject_b = _text(a.get("subject")), _text(b.get("subject"))
    if subject_a and subject_b and not _similar(subject_a, subject_b):
        return False
    return True


def mark_duplicates(items, existing):
    """Adds a 'note' to every item: '' if new, or the reason it looks like a duplicate."""
    result, accepted = [], []
    for item in items:
        note = ""
        if any(is_duplicate(item, e) for e in existing):
            note = "Already in your deadlines"
        else:
            match = next((a for a in accepted if is_duplicate(item, a)), None)
            if match:
                note = f"Duplicate of '{match['title']}' ({match.get('source') or 'another image'})"

        row = dict(item)
        row["note"] = note
        result.append(row)
        if not note:
            accepted.append(item)
    return result


def find_internal_duplicates(records):
    """Pairs of rows inside one list that look the same: [(title_a, title_b, date), ...]"""
    pairs = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            if is_duplicate(records[i], records[j]):
                pairs.append((records[i]["title"], records[j]["title"], records[i]["date"]))
    return pairs