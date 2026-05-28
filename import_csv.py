"""
One-time script: import records2.csv into Firestore.

Usage:
    export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/firebase-credentials.json"
    python import_csv.py

Prerequisites:
    1. Download your Firebase Admin SDK service account key (JSON).
    2. Set the GOOGLE_APPLICATION_CREDENTIALS environment variable to point to it.
    3. Ensure you have the `firebase-admin` package installed (`pip install firebase-admin`).
"""

import csv
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

from record_store import generate_sorting_key, process_record_fields

# --- Configuration ---
CSV_PATH = Path(__file__).parent / "records_full_headed.csv"

COLLECTION = "records"


def _parse_row(row: dict) -> dict:
    """Convert a raw CSV row to the Firestore document schema."""
    id_letter = row.get("id_letter", "").strip() if "id_letter" in row else ""
    artist = str(row.get("artist", "")).strip() if "artist" in row else ""
    name = str(row.get("name", "")).strip() if "name" in row and row.get("name") else None
    
    data = {
        "box": int(row["box"]) if row.get("box") else 1,
        "id_letter": id_letter,
        "artist": artist,
        "name": name,
        "notes": row.get("notes") if row.get("notes") else None
    }
    return process_record_fields(data)



def main():
    load_dotenv()

    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Please set it to the path of your Firebase Admin service account JSON file.")
        print("Example: export GOOGLE_APPLICATION_CREDENTIALS='/path/to/key.json'")
        sys.exit(1)

    import firebase_admin
    from firebase_admin import credentials, firestore
    
    # Initialize Firebase Admin using Application Default Credentials
    if not firebase_admin._apps:
        # Without explicit credentials, firebase_admin automatically looks for 
        # GOOGLE_APPLICATION_CREDENTIALS in the environment.
        firebase_admin.initialize_app()
        
    db = firestore.client()

    if not CSV_PATH.exists():
        print(f"CSV not found at {CSV_PATH}")
        sys.exit(1)

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        
        # Insert efficiently in batches (Firestore allows up to 500 ops per batch)
        BATCH_SIZE = 500
        total_records = len(reader)
        imported_count = 0
        
        for i in range(0, total_records, BATCH_SIZE):
            batch = db.batch()
            chunk = reader[i:i + BATCH_SIZE]
            
            for row in chunk:
                doc_data = _parse_row(row)
                doc_ref = db.collection(COLLECTION).document()
                batch.set(doc_ref, doc_data)
                
            batch.commit()
            imported_count += len(chunk)
            print(f"Batch committed: {imported_count}/{total_records} records imported.")

    print(f"\nDone. Successfully imported {imported_count} records into Firestore.")


if __name__ == "__main__":
    main()
