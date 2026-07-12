"""
Database client initialization.

This is the only module that knows about Firebase/Firestore.
If the backing store changes, only this file needs updating.

gRPC SEGFAULT FIX (Streamlit Cloud / Linux):
  grpcio is fork-unsafe. Streamlit's internal threading triggers a native
  segfault unless GRPC_ENABLE_FORK_SUPPORT=1 is set before any gRPC import.
  These env vars MUST be set before 'firebase_admin' is imported anywhere,
  so this file must be imported first (it is, via app.py → db_client).
"""

import os

# Set before any grpcio import — prevents segfault on Linux (Streamlit Cloud).
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "1")
os.environ.setdefault("GRPC_POLL_STRATEGY", "poll")

import streamlit as st
from firebase_admin import credentials, firestore, _apps, initialize_app


def get_db() -> firestore.firestore.Client:
    """Return a Firestore client, initialising the Firebase app once."""
    if not _apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        initialize_app(cred)
    return firestore.client()
