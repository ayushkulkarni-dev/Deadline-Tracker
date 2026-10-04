from database import init_db
from email_reminders import send_pending_emails

init_db()
sent, errors = send_pending_emails()
print(f"Sent {sent} email(s)")
for e in errors:
    print("ERROR:", e)