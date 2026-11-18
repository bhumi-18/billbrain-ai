"""
auth.py — Authentication module for BillBrain AI.

Currently implements a mock login flow for development.
Replace the marked sections with real Google OAuth when deploying to production.

Production OAuth options:
  - streamlit-google-auth: https://github.com/MrBounty/streamlit-google-auth
  - authlib: https://docs.authlib.org/en/latest/
"""

import time
import streamlit as st

# ── Session state keys ────────────────────────────────────────────────────────
_USER_KEY = "user"
_AUTH_ERROR_KEY = "auth_error"


# ── Core auth functions ───────────────────────────────────────────────────────

def get_current_user() -> dict | None:
    """
    Returns current user info from session state, or None if not logged in.

    Checks for token expiry: if the stored user dict contains an `expires_at`
    timestamp (Unix epoch) that is in the past, the session is cleared and
    an error message is set.
    """
    user = st.session_state.get(_USER_KEY)
    if user is None:
        return None

    # ── Token expiry check ────────────────────────────────────────────────────
    # In production, Google OAuth tokens include an `expires_at` field.
    # Replace this block with real token validation if using authlib/google-auth.
    expires_at = user.get("expires_at")
    if expires_at is not None and time.time() > expires_at:
        logout()
        st.session_state[_AUTH_ERROR_KEY] = "🔒 Session expired. Please log in again."
        return None

    return user


def is_authenticated() -> bool:
    """Returns True if a valid user is present in session state."""
    return get_current_user() is not None


def logout() -> None:
    """Clears all session state keys (full sign-out)."""
    st.session_state.clear()


def login() -> dict | None:
    """
    Shows login UI. In production, redirects to Google OAuth.
    In development, shows a simple form to enter user details manually.

    Returns the user dict if authenticated, None otherwise.

    ── Production replacement ────────────────────────────────────────────────
    Replace the form below with:

        from streamlit_google_auth import Authenticate
        auth = Authenticate(
            secret_credentials_path="google_credentials.json",
            cookie_name="billbrain_auth",
            cookie_key=st.secrets["COOKIE_KEY"],
            redirect_uri=st.secrets["OAUTH_REDIRECT_URI"],
        )
        auth.check_authentification()
        if auth.is_connected():
            return {"user_id": auth.id, "email": auth.email, "name": auth.name}
        auth.login()
        return None
    ─────────────────────────────────────────────────────────────────────────
    """
    # Show any pending auth error (e.g. session expired)
    error = st.session_state.pop(_AUTH_ERROR_KEY, None)
    if error:
        st.warning(error)

    st.subheader("🔐 Sign in to BillBrain AI")
    st.caption("Development mode — enter any email to continue. Replace with Google OAuth for production.")

    with st.form("dev_login_form"):
        email = st.text_input("Email address", placeholder="you@example.com")
        name = st.text_input("Display name", placeholder="Your Name")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        if not email or "@" not in email:
            st.error("Please enter a valid email address.")
            return None

        user = {
            "user_id": email.lower().strip(),
            "email": email.lower().strip(),
            "name": name.strip() or email.split("@")[0],
            # In production, set expires_at from the OAuth token's expiry time:
            # "expires_at": token["expires_at"],
        }
        st.session_state[_USER_KEY] = user
        st.rerun()

    return None


# ── UI component ──────────────────────────────────────────────────────────────

def render_login_button() -> None:
    """
    Renders a login/logout button in the Streamlit UI header area.
    Shows the signed-in user's name and a Logout button when authenticated,
    or a Login button when not authenticated.
    """
    user = get_current_user()

    # Show any auth error that was set (e.g. after session expiry redirect)
    error = st.session_state.get(_AUTH_ERROR_KEY)
    if error:
        st.warning(error)

    col_spacer, col_auth = st.columns([8, 2])
    with col_auth:
        if user:
            st.caption(f"👤 {user.get('name', user.get('email', ''))}")
            if st.button("Logout", key="logout_btn", use_container_width=True):
                logout()
                st.rerun()
        else:
            if st.button("🔐 Login", key="login_btn", use_container_width=True):
                # Set a flag so the main app can show the login form
                st.session_state["show_login"] = True
                st.rerun()
