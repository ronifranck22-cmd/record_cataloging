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

def normalize_hebrew_text(text: str) -> tuple[str, str]:
    """
    Returns (translated_text, first_letter)
    e.g., '4 קולות' -> ('ארבעה קולות', 'א')
    """
    if not text:
        return "", ""
        
    text = text.strip()
    match = re.match(r'^(\d+)(.*)', text)
    if match:
        num_str = match.group(1)
        rest = match.group(2)
        num = int(num_str)
        
        hebrew_map = {
            0: "אפס", 1: "אחד", 2: "שניים", 3: "שלושה", 4: "ארבעה",
            5: "חמישה", 6: "שישה", 7: "שבעה", 8: "שמונה", 9: "תשעה",
            10: "עשר", 11: "אחת עשרה", 12: "שתים עשרה", 13: "שלוש עשרה",
            14: "ארבע עשרה", 15: "חמש עשרה", 16: "שש עשרה", 17: "שבע עשרה",
            18: "שמונה עשרה", 19: "תשע עשרה", 20: "עשרים", 30: "שלושים",
            40: "ארבעים", 50: "חמישים", 60: "שישים", 70: "שבעים",
            80: "שמונים", 90: "תשעים", 100: "מאה"
        }
        
        word = hebrew_map.get(num)
        if not word:
            first_digit = int(num_str[0])
            word = hebrew_map.get(first_digit, num_str)
            
        translated = word + rest
        return translated, word[0]
        
    letter = ""
    for char in text:
        if char.isalpha():
            letter = char
            break
    if not letter and text:
        letter = text[0]
        
    return text, letter

def process_record_fields(record: dict) -> dict:
    """Enriches the record by resolving digit prefixes to Hebrew words for sorting/id."""
    artist = record.get("artist", "") or ""
    name = record.get("name", "") or ""
    id_letter = str(record.get("id_letter", "") or "").strip()
    
    artist_translated, artist_letter = normalize_hebrew_text(artist)
    name_translated, name_letter = normalize_hebrew_text(name)
    
    if not id_letter or id_letter.isdigit():
        if artist_translated:
            id_letter = artist_letter
        elif name_translated:
            id_letter = name_letter
            
    record["id_letter"] = id_letter
    record["sorting_key"] = generate_sorting_key(id_letter, artist_translated, name_translated)
    return record



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
    record = process_record_fields(record)
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
            current_data = process_record_fields(current_data)
            fields["id_letter"] = current_data["id_letter"]
            fields["sorting_key"] = current_data["sorting_key"]
            
    db.collection(COLLECTION).document(doc_id).update(fields)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete(db, doc_id: str) -> None:
    """Delete a record by document ID."""
    db.collection(COLLECTION).document(doc_id).delete()
