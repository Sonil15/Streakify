"""
config.py
Centralizes all credential loading.
Supports both local .env (via python-dotenv) and Streamlit Cloud secrets (st.secrets).
"""

import os
import json
import streamlit as st


def _try_streamlit_secrets(key: str, default=None):
    """Safely pull a value from st.secrets without crashing outside Streamlit."""
    try:
        return st.secrets[key]
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Firebase client-side config (used by pyrebase4 for Auth)
# ---------------------------------------------------------------------------

def get_firebase_client_config() -> dict:
    """Return the Firebase web app config dict for pyrebase4."""
    # Streamlit Cloud: store as [firebase_client] table in secrets.toml
    secret = _try_streamlit_secrets("firebase_client")
    if secret:
        return dict(secret)

    # Local dev: plain env vars
    return {
        "apiKey":            os.getenv("FIREBASE_API_KEY", ""),
        "authDomain":        os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "databaseURL":       os.getenv("FIREBASE_DATABASE_URL", ""),
        "projectId":         os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket":     os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId":             os.getenv("FIREBASE_APP_ID", ""),
    }


# ---------------------------------------------------------------------------
# Firebase Admin / Firestore service-account config
# ---------------------------------------------------------------------------

def get_service_account_dict() -> dict:
    """
    Return the service-account JSON as a Python dict.

    Priority:
    1. Streamlit secret key  'firebase_service_account'  (JSON object)
    2. Env var  FIREBASE_SERVICE_ACCOUNT_JSON  (JSON string)
    3. Local file path  FIREBASE_SERVICE_ACCOUNT_PATH
    """
    # Streamlit Cloud: secrets.toml [firebase_service_account] block
    secret = _try_streamlit_secrets("firebase_service_account")
    if secret:
        return dict(secret)

    # JSON string in env (useful for CI / GitHub Actions)
    json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if json_str:
        return json.loads(json_str)

    # Local file path
    path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)

    raise RuntimeError(
        "No Firebase service-account credentials found. "
        "Set FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH, "
        "or add [firebase_service_account] to .streamlit/secrets.toml."
    )


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def get_telegram_token() -> str:
    token = _try_streamlit_secrets("TELEGRAM_BOT_TOKEN")
    if token:
        return str(token)
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def get_groq_api_key() -> str:
    token = _try_streamlit_secrets("GROQ_API_KEY")
    if token:
        return str(token)
    return os.getenv("GROQ_API_KEY", "")


# ---------------------------------------------------------------------------
# App-level constants
# ---------------------------------------------------------------------------

APP_NAME = "Streakify"
IST_OFFSET_HOURS = 5.5          # UTC+5:30
FREEZE_EARN_INTERVAL = 7        # consecutive days to earn 1 freeze
TIMEZONE = "Asia/Kolkata"
