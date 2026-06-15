"""
auth.py — URL-based admin session authentication
=================================================
Uses HMAC-SHA256-signed query parameters (?t=<token>&e=<expires_unix>)
to persist an admin session across page reloads without any browser
storage or iframe components.

HOW TO REVERT (3 steps, ~10 seconds):
  1. Delete this file (auth.py).
  2. In app.py, remove the two lines after the session-state init block:
         from auth import validate_session, login_success as _auth_login
         validate_session()
  3. Remove the single line inside set_admin():   _auth_login(entered)
  4. Remove the single line inside logout_admin(): st.query_params.clear()
  The app returns to its clean, no-persistence state instantly.

SECURITY MODEL:
  • The token is HMAC(key=password, msg=expires_timestamp).
  • Changing the expiry in the URL invalidates the token.
  • The session is valid for SESSION_DURATION_SECONDS (30 min).
  • The password itself is never stored or transmitted beyond the server.
"""

import hashlib
import hmac
import time

import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SESSION_DURATION_SECONDS: int = 1800  # 30 minutes


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_token(password: str, expires_ts: int) -> str:
    """Return HMAC-SHA256 hex digest of expires_ts, keyed by password."""
    return hmac.new(
        password.encode(),
        str(expires_ts).encode(),
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_session() -> None:
    """
    Read st.query_params and set st.session_state['is_admin'] = True when the
    URL token is valid and not expired.

    • Safe to call on every script rerun — never blocks, never calls st.stop().
    • If the token is expired or malformed, the params are cleared from the URL.
    • If is_admin is already True (same WebSocket session), skips validation
      to avoid unnecessary work.
    """
    # Already authenticated in this browser session — nothing to do.
    if st.session_state.get("is_admin"):
        return

    token: str = st.query_params.get("t", "")
    expires_raw: str = st.query_params.get("e", "")

    # No auth params in URL — silent no-op.
    if not token or not expires_raw:
        return

    # Parse expiry — reject malformed values.
    try:
        expires_ts = int(expires_raw)
    except (ValueError, TypeError):
        st.query_params.clear()
        return

    # Reject expired tokens.
    if time.time() >= expires_ts:
        st.query_params.clear()
        return

    # Load the server-side password.
    try:
        password = str(st.secrets["app_password"]).strip()
    except (KeyError, AttributeError):
        return  # Can't validate without a secret — leave params alone.

    # Constant-time HMAC comparison to prevent timing attacks.
    expected = _make_token(password, expires_ts)
    if hmac.compare_digest(token, expected):
        st.session_state["is_admin"] = True


def login_success(password: str) -> None:
    """
    Write a signed session token into the URL after a successful login.

    Call this from set_admin() immediately after setting is_admin = True.
    Streamlit will update the browser URL; the token is validated on the
    next rerun so the session survives page refreshes.

    Args:
        password: The *plaintext* password the user just verified against.
                  Used as the HMAC key — never stored or logged.
    """
    expires_ts = int(time.time()) + SESSION_DURATION_SECONDS
    token = _make_token(password, expires_ts)
    st.query_params["t"] = token
    st.query_params["e"] = str(expires_ts)


def logout() -> None:
    """
    Remove auth params from the URL.

    Call from logout_admin() alongside the session-state reset.
    The URL is cleared immediately; is_admin is managed by app.py.
    """
    st.query_params.clear()
