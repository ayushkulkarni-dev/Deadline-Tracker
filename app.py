import re
import json
import sqlite3
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from config import missing_config
from ai_helper import extract_deadlines, parse_deadlines, GeminiError
from database import (
    init_db, add_deadline, get_deadlines, update_deadline, delete_deadline,
    save_setting, get_setting,
)
from dedupe import mark_duplicates, find_internal_duplicates
from dashboard import render_dashboard
from reminders import render_reminders
from email_reminders import send_pending_emails
from notifier import send_deadline_email
from utils import days_left, is_valid_email
from validators import validate_image

st.set_page_config(page_title="AI Deadline Tracker", page_icon="📅", layout="wide")

try:
    init_db()
except sqlite3.Error as e:
    st.error(f"Database error ({type(e).__name__}). Check that the data/ folder exists and is writable.")
    st.stop()

DATA_COLUMNS = ["id", "title", "subject", "date", "time", "description", "source", "note"]
TEXT_COLUMNS = ["title", "subject", "time", "description", "source", "note"]
TIME_PATTERN = r"([01]\d|2[0-3]):[0-5]\d"
MAX_IMAGES = 10   # protects your Gemini quota


# ---------- Helpers ----------
def to_dataframe(items):
    """List of dicts -> DataFrame. Rows with a duplicate note get 'delete' pre-ticked."""
    df = pd.DataFrame(items, columns=DATA_COLUMNS)
    df["id"] = pd.to_numeric(df["id"], errors="coerce")      # NaN = not in database yet
    for col in TEXT_COLUMNS:
        df[col] = df[col].fillna("").astype(str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df.insert(0, "delete", (df["note"] != "").astype(bool))
    return df


def tidy(df):
    """Drop the delete column, strip text, convert dates. Keeps id."""
    df = df.drop(columns=["delete"], errors="ignore").copy()
    for col in TEXT_COLUMNS:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def clean_rows(df):
    df = tidy(df)
    return df[df["title"] != ""].reset_index(drop=True)


def table_as_items(df):
    """Current table rows as plain dicts, used to compare new extractions against."""
    t = clean_rows(df)
    t["date"] = t["date"].dt.strftime("%Y-%m-%d").fillna("")
    return t[["title", "subject", "date", "source"]].to_dict("records")


def reload_from_db():
    st.session_state["deadlines_df"] = to_dataframe(get_deadlines())
    st.session_state["editor_version"] += 1


# ---------- Session state and settings ----------
if "editor_version" not in st.session_state:
    st.session_state["editor_version"] = 0     # changing this resets the editor widget
if "deadlines_df" not in st.session_state:
    st.session_state["deadlines_df"] = to_dataframe(get_deadlines())

saved_offsets = json.loads(get_setting("reminder_offsets", "[1]"))

# ---------- Auto-send reminder emails once per session ----------
if "emails_checked" not in st.session_state:
    st.session_state["emails_checked"] = True
    if get_setting("email_auto", "0") == "1":
        sent, errors = send_pending_emails()
        if sent:
            st.toast(f"📧 Sent {sent} reminder email(s)")
        for err in errors:
            st.toast(f"⚠️ {err}")

# ---------- Title, reminders, dashboard ----------
st.title("📅 AI Deadline Tracker")
st.caption("Upload images, let Gemini extract deadlines, then review and save them.")
st.divider()

render_reminders(saved_offsets)
render_dashboard()
st.divider()

# ---------- 1. Upload and extract (multiple images) ----------
st.header("1. Upload Images")
uploaded_files = st.file_uploader(
    "Upload syllabus / timetable / assignment images (you can select many)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.caption(f"{len(uploaded_files)} image(s) selected")
    with st.expander("Preview images", expanded=len(uploaded_files) <= 3):
        cols = st.columns(3)
        for i, file in enumerate(uploaded_files):
            with cols[i % 3]:
                st.image(file, caption=file.name, use_container_width=True)

    if st.button("✨ Extract with Gemini"):
        files = uploaded_files[:MAX_IMAGES]
        if len(uploaded_files) > MAX_IMAGES:
            st.warning(f"Only the first {MAX_IMAGES} images were processed.")

        all_items, summary, raw = [], [], {}
        progress = st.progress(0.0)

        for i, file in enumerate(files):
            progress.progress(i / len(files), text=f"Reading {file.name} ({i + 1}/{len(files)})")

            ok, mime, problem = validate_image(file)
            if not ok:
                summary.append({"image": file.name, "deadlines found": 0, "status": f"Skipped: {problem}"})
                continue

            try:
                text = extract_deadlines(file.getvalue(), mime)
                raw[file.name] = text
                items = parse_deadlines(text)
                for item in items:
                    item["source"] = file.name
                all_items += items
                summary.append({"image": file.name, "deadlines found": len(items), "status": "OK"})
            except GeminiError as e:
                summary.append({"image": file.name, "deadlines found": 0, "status": f"Failed: {e}"})
                if e.fatal:
                    st.error(f"Stopped: {e}")
                    break
            except ValueError:
                summary.append({"image": file.name, "deadlines found": 0,
                                "status": "Failed: Gemini's answer wasn't valid JSON. Try again or use a clearer image."})

        progress.empty()
        st.session_state["raw_results"] = raw
        st.session_state["extract_summary"] = summary

        # detect duplicates against saved deadlines AND rows already in the table
        existing = table_as_items(st.session_state["deadlines_df"]) + get_deadlines()
        marked = mark_duplicates(all_items, existing)
        duplicates = sum(1 for m in marked if m["note"])

        if marked:
            st.session_state["deadlines_df"] = pd.concat(
                [st.session_state["deadlines_df"], to_dataframe(marked)],
                ignore_index=True,
            )
            st.session_state["editor_version"] += 1
            st.success(f"Found {len(all_items)} deadline(s) in {len(files)} image(s). "
                       f"{duplicates} duplicate(s) detected.")
            if duplicates:
                st.info("Duplicates are pre-ticked in the table. Click 'Delete selected' to remove "
                        "them, or untick any that are not really duplicates.")
        else:
            st.warning("No deadlines could be extracted. Check the summary below.")

if "extract_summary" in st.session_state:
    with st.expander("Extraction summary (per image)", expanded=True):
        st.dataframe(pd.DataFrame(st.session_state["extract_summary"]), use_container_width=True)

if "raw_results" in st.session_state:
    with st.expander("Raw Gemini responses (for debugging)"):
        for name, text in st.session_state["raw_results"].items():
            st.caption(name)
            st.code(text, language="json")

st.divider()

# ---------- 2. Review table ----------
st.header("2. Review Deadlines")
st.caption("Edit cells, tick 'Delete?' and click delete, or add a deadline below. "
           "Nothing reaches the database until you click Save.")

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))
if "flash_warn" in st.session_state:
    st.warning(st.session_state.pop("flash_warn"))

edited_df = st.data_editor(
    st.session_state["deadlines_df"],
    num_rows="dynamic",
    use_container_width=True,
    key=f"editor_{st.session_state['editor_version']}",
    column_order=["delete", "title", "subject", "date", "time", "description", "source", "note"],
    column_config={
        "delete": st.column_config.CheckboxColumn("Delete?", default=False),
        "title": "Title",
        "subject": "Subject",
        "date": st.column_config.DateColumn("Date"),
        "time": st.column_config.TextColumn("Time (HH:MM)"),
        "description": "Description",
        "source": st.column_config.TextColumn("Image", disabled=True),
        "note": st.column_config.TextColumn("Note", disabled=True),
    },
)

btn1, btn2, _ = st.columns([1, 1, 4])

# ---------- Delete selected (table only; database changes on Save) ----------
if btn1.button("🗑 Delete selected"):
    marked_rows = edited_df["delete"].fillna(False).astype(bool)
    st.session_state["deadlines_df"] = edited_df[~marked_rows].reset_index(drop=True)
    st.session_state["editor_version"] += 1
    st.rerun()

# ---------- Save (syncs the table with SQLite) ----------
if btn2.button("💾 Save deadlines"):
    df = tidy(edited_df)
    df = df[~((df["title"] == "") & df["id"].isna())].reset_index(drop=True)

    errors = []
    if (df["title"] == "").any():
        errors.append("Every deadline needs a title.")
    if df["date"].isna().any():
        errors.append("Some rows have a missing or invalid date.")
    bad_time = (df["time"] != "") & ~df["time"].str.fullmatch(TIME_PATTERN)
    if bad_time.any():
        errors.append("Some times are not in HH:MM format (example: 14:30).")

    if errors:
        for e in errors:
            st.error(e)
    else:
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")
        duplicate_pairs = find_internal_duplicates(df.to_dict("records"))

        old_ids = {row["id"] for row in get_deadlines()}
        kept_ids = set()

        for _, r in df.iterrows():
            values = (r["title"], r["subject"], r["date"], r["time"], r["description"])
            if pd.notna(r["id"]):
                update_deadline(int(r["id"]), *values)      # existing row
                kept_ids.add(int(r["id"]))
            else:
                add_deadline(*values)                       # new row

        for removed_id in old_ids - kept_ids:               # rows removed from the table
            delete_deadline(removed_id)

        reload_from_db()
        st.session_state["flash"] = f"Saved {len(df)} deadlines to the database."
        if duplicate_pairs:
            shown = "; ".join(f"{a} / {b} ({d})" for a, b, d in duplicate_pairs[:5])
            more = " ..." if len(duplicate_pairs) > 5 else ""
            st.session_state["flash_warn"] = f"Possible duplicates were saved: {shown}{more}"
        st.rerun()

# ---------- Add manually ----------
st.subheader("➕ Add a deadline manually")
with st.form("add_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    new_title = c1.text_input("Title *")
    new_subject = c2.text_input("Subject")
    c3, c4 = st.columns(2)
    new_date = c3.date_input("Date", value=date.today())
    new_time = c4.text_input("Time (HH:MM, optional)")
    new_desc = st.text_input("Description")
    submitted = st.form_submit_button("Add deadline")

if submitted:
    if not new_title.strip():
        st.warning("Title is required.")
    elif new_time.strip() and not re.fullmatch(TIME_PATTERN, new_time.strip()):
        st.warning("Time must be in HH:MM format, like 14:30.")
    else:
        new_row = to_dataframe([{
            "title": new_title.strip(),
            "subject": new_subject.strip(),
            "date": new_date.isoformat(),
            "time": new_time.strip(),
            "description": new_desc.strip(),
            "source": "Manual",
        }])
        st.session_state["deadlines_df"] = pd.concat(
            [edited_df, new_row], ignore_index=True    # edited_df keeps unsaved edits
        )
        st.session_state["editor_version"] += 1
        st.rerun()

# ---------- Sidebar ----------
with st.sidebar:
    # ----- Reminder settings -----
    st.header("🔔 Reminder Settings")
    missing = missing_config()
    if missing:
        st.warning("Missing config (.env locally, Secrets on Streamlit Cloud): " + ", ".join(missing))
    choice = st.multiselect(
        "Remind me before",
        [1, 2, 7],
        default=saved_offsets,
        format_func=lambda n: f"{n} day{'s' if n > 1 else ''} before",
    )
    if st.button("Save settings"):
        save_setting("reminder_offsets", json.dumps(sorted(choice)))
        st.success("Reminder settings saved.")
        st.rerun()

    st.divider()

    # ----- Email receiver -----
    st.subheader("📧 Email Notifications")
    receiver = st.text_input(
        "Send reminders to",
        value=get_setting("receiver_email", ""),
        placeholder="you@example.com",
    )
    if st.button("Save email"):
        if is_valid_email(receiver):
            save_setting("receiver_email", receiver.strip())
            st.success("Email saved.")
            st.rerun()
        else:
            st.error("Enter a valid email address.")

    # ----- Auto-send + manual send -----
    auto_on = st.toggle(
        "Auto-send emails when app opens",
        value=get_setting("email_auto", "0") == "1",
    )
    if auto_on != (get_setting("email_auto", "0") == "1"):
        save_setting("email_auto", "1" if auto_on else "0")

    if st.button("Send pending reminder emails now"):
        with st.spinner("Sending..."):
            sent, errors = send_pending_emails()
        if sent:
            st.success(f"Sent {sent} reminder email(s).")
        elif not errors:
            st.info("No pending reminders to email.")
        for err in errors:
            st.error(err)

    st.divider()

    # ----- Email test -----
    saved = get_deadlines()
    options = ["Sample deadline"] + [f"{d['title']} ({d['date']})" for d in saved]
    pick = st.selectbox(
        "Send test for",
        range(len(options)),
        format_func=lambda i: options[i],
    )

    if st.button("Send test email"):
        target = receiver.strip()

        if target and not is_valid_email(target):
            st.error("Enter a valid email address first.")
        else:
            if pick == 0:
                payload = dict(
                    title="Test Deadline",
                    subject="DBMS",
                    due_date=(date.today() + timedelta(days=3)).isoformat(),
                    days_remaining=3,
                )
            else:
                d = saved[pick - 1]
                payload = dict(
                    title=d["title"],
                    subject=d["subject"] or "",
                    due_date=d["date"],
                    days_remaining=days_left(d["date"]),
                )

            with st.spinner("Sending..."):
                ok, message = send_deadline_email(**payload, receiver=target or None)

            if ok:
                st.success(message)
            else:
                st.error(message)
