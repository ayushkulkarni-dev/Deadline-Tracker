import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path('data/deadlines.db')

def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)     
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with closing(get_connection()) as conn, conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS emails_sent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deadline_id INTEGER NOT NULL,
            days_before INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            UNIQUE (deadline_id, days_before, due_date)
            )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders_sent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deadline_id INTEGER NOT NULL,
            days_before INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            UNIQUE (deadline_id, days_before, due_date)
            )
        """)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deadlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subject TEXT,
                date TEXT NOT NULL,
                time TEXT,
                description TEXT
            )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

def save_setting(key, value):
    with closing(get_connection()) as conn, conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )    

def get_setting(key, default=None):
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default    

def was_sent(deadline_id, days_before, due_date):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT 1 FROM reminders_sent WHERE deadline_id=? AND days_before=? AND due_date=?",
            (deadline_id, days_before, due_date),
        ).fetchone()
        return row is not None

def mark_sent(deadline_id, days_before, due_date):
    with closing(get_connection()) as conn, conn:
        conn.execute(
            "INSERT OR IGNORE INTO reminders_sent (deadline_id, days_before, due_date) VALUES (?, ?, ?)",
            (deadline_id, days_before, due_date),
        )

def email_was_sent(deadline_id, days_before, due_date):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT 1 FROM emails_sent WHERE deadline_id=? AND days_before=? AND due_date=?",
            (deadline_id, days_before, due_date),
        ).fetchone()
        return row is not None


def mark_email_sent(deadline_id, days_before, due_date):
    with closing(get_connection()) as conn, conn:
        conn.execute(
            "INSERT OR IGNORE INTO emails_sent (deadline_id, days_before, due_date) VALUES (?, ?, ?)",
            (deadline_id, days_before, due_date),
        )

def add_deadline(title, subject, date, time, description):
    with closing(get_connection()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO deadlines (title, subject, date, time, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, subject, date, time, description),
        )
        return cur.lastrowid

def get_deadlines():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT * FROM deadlines ORDER BY date, time"
        ).fetchall()
        return [dict(row) for row in rows]

def update_deadline(deadline_id, title, subject, date, time, description):
    with closing(get_connection()) as conn, conn:
        conn.execute(
            "UPDATE deadlines SET title=?, subject=?, date=?, time=?, description=? "
            "WHERE id=?",
            (title, subject, date, time, description, deadline_id),
        )

def delete_deadline(deadline_id):
    with closing(get_connection()) as conn, conn:
        conn.execute("DELETE FROM reminders_sent WHERE deadline_id=?", (deadline_id,))
        conn.execute("DELETE FROM emails_sent WHERE deadline_id=?", (deadline_id,))
        conn.execute("DELETE FROM deadlines WHERE id=?", (deadline_id,))

if __name__ == "__main__":
    init_db()
    new_id = add_deadline("DBMS Assignment", "DBMS", "2026-10-10", "17:00", "Unit 3")
    print(get_deadlines())
    update_deadline(new_id, "DBMS Assignment 2", "DBMS", "2026-10-11", "17:00", "Unit 3")
    print(get_deadlines())
    delete_deadline(new_id)
    print(get_deadlines())