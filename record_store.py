"""
CRUD operations for the records collection.

All business logic for reading/writing records lives here.
This module is backend-agnostic — it receives a Firestore client
from db_client but defines *what* data operations look like.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

COLLECTION = "records"

FIELDS = ["box", "artist", "name", "version", "tag"]


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_all(db) -> pd.DataFrame:
    """Fetch every record and return as a DataFrame."""
    docs = db.collection(COLLECTION).stream()
    rows = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        rows.append(data)

    if not rows:
        return pd.DataFrame(columns=["id"] + FIELDS)

    df = pd.DataFrame(rows)
    # Ensure consistent column order
    for col in FIELDS:
        if col not in df.columns:
            df[col] = None
    df = df[["id"] + FIELDS]
    return df


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def add(db, record: dict) -> str:
    """Add a single record. Returns the new document ID."""
    doc_ref = db.collection(COLLECTION).document()
    doc_ref.set(record)
    return doc_ref.id


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def update(db, doc_id: str, fields: dict) -> None:
    """Update specific fields on an existing record."""
    db.collection(COLLECTION).document(doc_id).update(fields)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete(db, doc_id: str) -> None:
    """Delete a record by document ID."""
    db.collection(COLLECTION).document(doc_id).delete()
