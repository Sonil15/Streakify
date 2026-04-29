"""
auth.py
Firebase Authentication using pyrebase4.
Handles sign-up, login, logout, and session-state management.
"""

import pyrebase
import streamlit as st
from datetime import datetime, timedelta
from config import get_firebase_client_config
import database as db

try:
    import extra_streamlit_components as stx
except ModuleNotFoundError:
    stx = None


# ---------------------------------------------------------------------------
# Initialisation (cached so Firebase is only initialised once)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _get_pyrebase_auth():
    config = get_firebase_client_config()
    firebase = pyrebase.initialize_app(config)
    return firebase.auth()


def get_auth():
    return _get_pyrebase_auth()

def _get_cookie_manager():
    if stx is None:
        return None
    if "_cookie_manager" not in st.session_state:
        st.session_state["_cookie_manager"] = stx.CookieManager()
    return st.session_state["_cookie_manager"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def signup(email: str, password: str, display_name: str) -> tuple[bool, str]:
    """
    Create a new Firebase Auth user + matching Firestore profile.
    Returns (success: bool, message: str).
    """
    auth = get_auth()
    try:
        user = auth.create_user_with_email_and_password(email, password)
        uid = user["localId"]
        id_token = user["idToken"]
        refresh_token = user.get("refreshToken", "")

        # Persist a Firestore user profile
        db.create_user_profile(uid, {
            "email": email,
            "display_name": display_name,
            "telegram_chat_id": "",
            "accountability_partner_id": "",
        })

        # Store session
        _set_session(uid, id_token, email, display_name)
        _persist_login(refresh_token)
        return True, "Account created! Welcome to Streakify 🎉"

    except Exception as e:
        return False, _parse_firebase_error(e)


def login(email: str, password: str) -> tuple[bool, str]:
    """
    Sign in an existing user.
    Returns (success: bool, message: str).
    """
    auth = get_auth()
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        uid = user["localId"]
        id_token = user["idToken"]
        refresh_token = user.get("refreshToken", "")

        profile = db.get_user_profile(uid)
        display_name = profile.get("display_name", email.split("@")[0]) if profile else email.split("@")[0]

        _set_session(uid, id_token, email, display_name)
        _persist_login(refresh_token)
        return True, f"Welcome back, {display_name}! 👋"

    except Exception as e:
        return False, _parse_firebase_error(e)


def logout():
    """Clear all auth-related session state."""
    for key in ["uid", "id_token", "email", "display_name", "logged_in"]:
        st.session_state.pop(key, None)
    _clear_persistent_login()


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def get_current_user() -> dict | None:
    if not is_logged_in():
        return None
    return {
        "uid":          st.session_state.get("uid"),
        "id_token":     st.session_state.get("id_token"),
        "email":        st.session_state.get("email"),
        "display_name": st.session_state.get("display_name"),
    }


def try_restore_session() -> bool:
    """
    Restore auth session from a long-lived refresh-token cookie.
    Returns True when a valid session is available.
    """
    if is_logged_in():
        return True

    cookie_mgr = _get_cookie_manager()
    if cookie_mgr is None:
        return False
    refresh_token = cookie_mgr.get(_refresh_cookie_name())
    if not refresh_token:
        return False

    auth = get_auth()
    try:
        refreshed = auth.refresh(refresh_token)
        id_token = refreshed["idToken"]
        new_refresh = refreshed.get("refreshToken", refresh_token)
        uid = refreshed.get("userId") or refreshed.get("localId")
        if not uid:
            _clear_persistent_login()
            return False

        account_info = auth.get_account_info(id_token)
        users = account_info.get("users", [])
        email = users[0].get("email", "") if users else ""

        profile = db.get_user_profile(uid)
        display_name = (
            profile.get("display_name", email.split("@")[0])
            if profile else email.split("@")[0]
        )

        _set_session(uid, id_token, email, display_name)
        _persist_login(new_refresh)
        return True
    except Exception:
        _clear_persistent_login()
        return False


def send_password_reset(email: str) -> tuple[bool, str]:
    auth = get_auth()
    try:
        auth.send_password_reset_email(email)
        return True, "Password reset email sent! Check your inbox 📬"
    except Exception as e:
        return False, _parse_firebase_error(e)


# ---------------------------------------------------------------------------
# Auth UI
# ---------------------------------------------------------------------------

def render_auth_page():
    """Render the full login / sign-up / password-reset UI."""
    from styles import inject_custom_css
    inject_custom_css()

    st.markdown(
        """
        <div style='text-align:center; padding: 2rem 0 1rem;'>
            <span style='font-size: 3.5rem;'>🔥</span>
            <h1 style='font-size:2.8rem; font-weight:800; color:#6C63FF; margin:0;'>Streakify</h1>
            <p style='color:#888; font-size:1.05rem; margin-top:0.3rem;'>
                Build habits. Break limits. Keep your streak. ✨
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_signup, tab_reset = st.tabs(["🔑 Login", "✨ Sign Up", "🔒 Reset Password"])

    # --- Login ---
    with tab_login:
        with st.form("login_form"):
            st.markdown("### Welcome back! 👋")
            email    = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Login 🚀", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please fill in all fields.")
            else:
                with st.spinner("Logging in..."):
                    ok, msg = login(email, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # --- Sign Up ---
    with tab_signup:
        with st.form("signup_form"):
            st.markdown("### Create your account 🌟")
            name     = st.text_input("Display Name", placeholder="Your Name")
            email    = st.text_input("Email", placeholder="you@example.com", key="su_email")
            password = st.text_input("Password", type="password", placeholder="min 6 characters", key="su_pw")
            confirm  = st.text_input("Confirm Password", type="password", placeholder="same as above", key="su_confirm")
            submitted = st.form_submit_button("Create Account 🎉", use_container_width=True)

        if submitted:
            if not all([name, email, password, confirm]):
                st.error("Please fill in all fields.")
            elif password != confirm:
                st.error("Passwords don't match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                with st.spinner("Creating your account..."):
                    ok, msg = signup(email, password, name)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # --- Reset ---
    with tab_reset:
        with st.form("reset_form"):
            st.markdown("### Reset your password 🔒")
            email = st.text_input("Email", placeholder="you@example.com", key="reset_email")
            submitted = st.form_submit_button("Send Reset Email 📬", use_container_width=True)

        if submitted:
            if not email:
                st.error("Please enter your email.")
            else:
                ok, msg = send_password_reset(email)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_session(uid: str, id_token: str, email: str, display_name: str):
    st.session_state["uid"]          = uid
    st.session_state["id_token"]     = id_token
    st.session_state["email"]        = email
    st.session_state["display_name"] = display_name
    st.session_state["logged_in"]    = True


def _refresh_cookie_name() -> str:
    return "streakify_refresh_token"


def _persist_login(refresh_token: str):
    if not refresh_token:
        return
    cookie_mgr = _get_cookie_manager()
    if cookie_mgr is None:
        return
    cookie_mgr.set(
        _refresh_cookie_name(),
        refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )


def _clear_persistent_login():
    cookie_mgr = _get_cookie_manager()
    if cookie_mgr is None:
        return
    cookie_mgr.delete(_refresh_cookie_name())


def _parse_firebase_error(e: Exception) -> str:
    """Extract a human-readable error message from a Firebase exception."""
    msg = str(e)
    if "EMAIL_EXISTS" in msg:
        return "This email is already registered. Try logging in."
    if "EMAIL_NOT_FOUND" in msg or "INVALID_EMAIL" in msg:
        return "Email not found. Please check or sign up."
    if "INVALID_PASSWORD" in msg or "WRONG_PASSWORD" in msg:
        return "Incorrect password. Try again."
    if "WEAK_PASSWORD" in msg:
        return "Password is too weak. Use at least 6 characters."
    if "TOO_MANY_ATTEMPTS_TRY_LATER" in msg:
        return "Too many failed attempts. Please try again later."
    if "INVALID_LOGIN_CREDENTIALS" in msg:
        return "Invalid email or password."
    return "Something went wrong. Please try again."
