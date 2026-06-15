"""
auth.py — URL-based admin session authentication
=================================================
Uses HMAC-SHA256-signed query parameters (?t=<token>&e=<expires_unix>)
to persist an admin session across page reloads without any browser
storage or iframe components.

HOW TO REVERT (4 steps, ~30 seconds):
  1. Delete this file (auth.py).
  2. In app.py, remove the import+call block after session-state init:
         from auth import ...
         _auth_validate()
         _auth_flush()
  3. Remove `_auth_login(entered)` from set_admin().
  4. Remove `_auth_logout()` from logout_admin().
  The app returns to its clean, no-persistence state instantly.

SECURITY MODEL:
  • The token is HMAC(key=password, msg=expires_timestamp).
  • Changing the expiry in the URL invalidates the token.
  • The session is valid for SESSION_DURATION_SECONDS (30 min).
  • The password itself is never stored or transmitted.

WHY THE DEFERRED-WRITE PATTERN:
  Streamlit 1.55 does not reliably sync st.query_params writes that happen
  inside on_change callbacks to the browser URL bar. The write must happen
  in the main script body (not inside a callback). We solve this by:
    1. Callback (set_admin) → sets _auth_pending_write flag in session_state.
    2. Main script body (flush_pending) → sees the flag → writes to
       st.query_params → clears the flag. This runs on every rerun.
"""

import hashlib
import hmac
import time
from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SESSION_DURATION_SECONDS: int = 1800  # 30 minutes

# session_state key used to pass data from the callback to the main body
_PENDING_KEY = "_auth_pending_write"


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


def _get_password() -> Optional[str]:
    """Load the server-side password from secrets, or None on failure."""
    try:
        return str(st.secrets["app_password"]).strip()
    except (KeyError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Public API — called from app.py
# ---------------------------------------------------------------------------

def validate_session() -> None:
    """
    Read st.query_params and set st.session_state['is_admin'] = True when the
    URL token is valid and not expired.

    MUST be called at the top of the main script body on every rerun,
    after session-state defaults are initialised. Never blocks or calls
    st.stop().
    """
    # Already authenticated in this session — skip re-validation.
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

    password = _get_password()
    if not password:
        return  # Can't validate without a secret.

    # Constant-time comparison to prevent timing attacks.
    expected = _make_token(password, expires_ts)
    if hmac.compare_digest(token, expected):
        st.session_state["is_admin"] = True


def flush_pending() -> None:
    """
    Write any pending token into st.query_params.

    MUST be called in the main script body (NOT inside a callback) on every
    rerun, immediately after validate_session(). It reads the pending-write
    flag set by login_success() or logout() and applies it to query_params
    so the browser URL actually updates.
    """
    pending = st.session_state.pop(_PENDING_KEY, None)
    if pending is None:
        return

    action = pending.get("action")
    if action == "set":
        st.query_params["t"] = pending["token"]
        st.query_params["e"] = pending["expires"]
    elif action == "clear":
        st.query_params.clear()


def login_success(password: str) -> None:
    """
    Queue a signed URL token to be written on the next script body run.

    Call this from the set_admin() callback after setting is_admin = True.
    The actual st.query_params write is deferred to flush_pending() which
    runs in the main script body — this guarantees the browser URL updates.

    Args:
        password: The verified plaintext password. Used as the HMAC key.
    """
    expires_ts = int(time.time()) + SESSION_DURATION_SECONDS
    token = _make_token(password, expires_ts)
    st.session_state[_PENDING_KEY] = {
        "action": "set",
        "token": token,
        "expires": str(expires_ts),
    }


def logout() -> None:
    """
    Queue a URL clear to be applied on the next script body run.

    Call from logout_admin() alongside the session-state reset.
    """
    st.session_state[_PENDING_KEY] = {"action": "clear"}
