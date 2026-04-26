"""
CRUD operations for the records collection.

All business logic for reading/writing records lives here.
This module is backend-agnostic — it receives a Firestore client
from db_client but defines *what* data operations look like.
"""

from __future__ import annotations
import re
import pandas as pd

COLLECTION = "records"

FIELDS = ["box", "id_letter", "artist", "name", "notes"]


def extract_root(prefix_letter: str, text: str) -> str:
    """Find the first word in 'text' that matches 'prefix_letter', ignoring 'ה'."""
    if not text or not prefix_letter:
        return ""
    words = text.split()
    for w in words:
        if w.startswith(prefix_letter):
            return w
        if w.startswith("ה") and len(w) > 1 and w[1:].startswith(prefix_letter):
            return w[1:]
    return ""


def generate_sorting_key(id_letter: str, artist: str, name: str) -> str:
    """Generate a hidden sorting key prioritizing root word, falling back, and padding sequences."""
    id_l = str(id_letter).strip() if id_letter else ""
    artist_s = str(artist).strip() if artist else ""
    name_s = str(name).strip() if name else ""

    root = extract_root(id_l, artist_s)
    if not root:
        root = extract_root(id_l, name_s)
    if not root:
        root = artist_s if artist_s else (name_s if name_s else "")

    def pad_numbers(match):
        return f"{int(match.group(0)):05d}"
    
    root = re.sub(r'\d+', pad_numbers, root)
    name_padded = re.sub(r'\d+', pad_numbers, name_s)
    
    return f"{id_l}_{root}_{name_padded}"


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_all(db) -> pd.DataFrame:
    """Fetch all records ordered by sorting_key to perform Pandas filters."""
    query = db.collection(COLLECTION).order_by("sorting_key")
    docs = list(query.stream())
    
    rows = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        rows.append(data)

    if not rows:
        return pd.DataFrame(columns=["id", "sorting_key"] + FIELDS)

    df = pd.DataFrame(rows)
    for col in FIELDS + ["sorting_key"]:
        if col not in df.columns:
            df[col] = None
            
    ordered_cols = ["id", "sorting_key"] + FIELDS
    ordered_cols = [c for c in ordered_cols if c in df.columns]
    
    df = df[ordered_cols]
    return df


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def add(db, record: dict) -> str:
    """Add a single record. Returns the new document ID."""
    record["sorting_key"] = generate_sorting_key(
        record.get("id_letter", ""),
        record.get("artist", ""),
        record.get("name", "")
    )
    doc_ref = db.collection(COLLECTION).document()
    doc_ref.set(record)
    return doc_ref.id


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def update(db, doc_id: str, fields: dict) -> None:
    """Update specific fields on an existing record."""
    if any(k in fields for k in ["id_letter", "artist", "name"]):
        doc = db.collection(COLLECTION).document(doc_id).get()
        if doc.exists:
            current_data = doc.to_dict()
            current_data.update(fields)
            fields["sorting_key"] = generate_sorting_key(
                current_data.get("id_letter", ""),
                current_data.get("artist", ""),
                current_data.get("name", "")
            )
            
    db.collection(COLLECTION).document(doc_id).update(fields)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete(db, doc_id: str) -> None:
    """Delete a record by document ID."""
    db.collection(COLLECTION).document(doc_id).delete()
