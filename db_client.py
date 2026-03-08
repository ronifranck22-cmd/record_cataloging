"""
Database client initialization.

This is the only module that knows about Firebase/Firestore.
If the backing store changes, only this file needs updating.
"""

import streamlit as st
from firebase_admin import credentials, firestore, _apps, initialize_app


def get_db() -> firestore.firestore.Client:
    """Return a Firestore client, initialising the Firebase app once."""
    if not _apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        initialize_app(cred)
    return firestore.client()
