import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED = {
    "GEMINI_API_KEY": "Gemini API key",
    "EMAIL_SENDER": "Email sender",
    "EMAIL_APP_PASSWORD": "Email app password",
}


def missing_config():
    """Returns labels only, never the secret values."""
    return [label for key, label in REQUIRED.items() if not os.getenv(key)]