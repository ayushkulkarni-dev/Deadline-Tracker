import os
import smtplib
import ssl
from email.message import EmailMessage

from dotenv import load_dotenv

from utils import days_label

load_dotenv()

SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
RECEIVER = os.getenv("EMAIL_RECEIVER")


def build_message(title, subject, due_date, days_remaining, receiver):
    label = days_label(days_remaining)          # "3 days left", "Due today", ...

    msg = EmailMessage()
    msg["Subject"] = f"⏰ Reminder: {title} - {label}"
    msg["From"] = SENDER
    msg["To"] = receiver
    msg.set_content(
        "Deadline Reminder\n"
        "-----------------\n"
        f"Title: {title}\n"
        f"Subject: {subject or '-'}\n"
        f"Due date: {due_date}\n"
        f"Days remaining: {days_remaining} ({label})\n"
    )
    return msg


def send_deadline_email(title, subject, due_date, days_remaining, receiver=None):
    """Returns (ok, message). Never raises, so the app can't crash on email errors."""
    receiver = receiver or RECEIVER
    if not (SENDER and PASSWORD and receiver):
        return False, "Email settings missing in .env (restart Streamlit after editing it)."

    msg = build_message(title, subject, due_date, days_remaining, receiver)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=15) as server:
            server.login(SENDER, PASSWORD)
            server.send_message(msg)
        return True, f"Email sent to {receiver}"
    except smtplib.SMTPAuthenticationError:
        return False, "Login failed: check your email and App Password."
    except Exception as e:
        return False, f"Could not send email: {e}"


if __name__ == "__main__":
    # run: python notifier.py
    print(send_deadline_email("Test Deadline", "DBMS", "2026-10-10", 3))