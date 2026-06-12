#!/usr/bin/env python3
"""
db_cleanup.py — Firestore catalog cleanup.

Identifies and deletes entirely empty records (where both artist and album name fields
are blank, null, or whitespace).

Usage:
    # Dry-run: list empty records
    python db_cleanup.py
    
    # Commit: delete empty records
    python db_cleanup.py --commit
"""

import os
import sys
import json
import argparse
import firebase_admin
from firebase_admin import credentials, firestore

def main():
    parser = argparse.ArgumentParser(
        description="Clean up empty records from Firestore."
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually delete the empty records from Firestore"
    )
    args = parser.parse_args()

    sdk_key = "firebase-adminsdk.json"
    if not os.path.exists(sdk_key):
        print(f"Error: Firestore service account key file '{sdk_key}' is missing in the project folder.")
        sys.exit(1)

    # Initialize Firebase
    if not firebase_admin._apps:
        cred = credentials.Certificate(sdk_key)
        firebase_admin.initialize_app(cred)
    db = firestore.client()

    print("Scanning Firestore collection 'records' for empty records...")
    docs = list(db.collection("records").stream())
    
    empty_records = []
    for doc in docs:
        data = doc.to_dict()
        artist = str(data.get("artist", "") or "").strip()
        name = str(data.get("name", "") or "").strip()
        
        # Check if both fields are entirely blank or null
        if not artist and not name:
            empty_records.append((doc.id, data))

    if not empty_records:
        print("🎉 No empty records found in Firestore. Database is clean!")
        sys.exit(0)

    print(f"\n🔍 Found {len(empty_records)} empty records:")
    for doc_id, data in empty_records:
        print(f"  ID: {doc_id} | Box: {data.get('box', 'N/A')} | Notes: {data.get('notes', '')}")

    if args.commit:
        print(f"\nDeleting {len(empty_records)} empty records from Firestore...")
        batch = db.batch()
        count = 0
        deleted_count = 0
        
        for doc_id, _ in empty_records:
            doc_ref = db.collection("records").document(doc_id)
            batch.delete(doc_ref)
            count += 1
            deleted_count += 1
            
            # Firestore batch limit is 500
            if count >= 400:
                batch.commit()
                batch = db.batch()
                count = 0
                
        if count > 0:
            batch.commit()
            
        print(f"✅ Success! Deleted {deleted_count} empty records.")
    else:
        print(f"\nTo delete these {len(empty_records)} records, rerun this command with the '--commit' flag:")
        print("  python db_cleanup.py --commit")

if __name__ == "__main__":
    main()
