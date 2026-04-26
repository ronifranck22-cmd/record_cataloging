"""
Script: clear_db.py
Purpose: Deletes all documents within the 'records' collection in Firestore.

Usage:
    export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/firebase-credentials.json"
    python clear_db.py
"""

import sys
import os
from dotenv import load_dotenv

COLLECTION = "records"

def main():
    load_dotenv()

    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Please set it to the path of your Firebase Admin service account JSON file.")
        print("Example: export GOOGLE_APPLICATION_CREDENTIALS='/path/to/key.json'")
        sys.exit(1)

    import firebase_admin
    from firebase_admin import credentials, firestore
    
    # Initialize Firebase Admin
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
        
    db = firestore.client()

    print(f"Fetching all documents from '{COLLECTION}' to delete...")
    docs = db.collection(COLLECTION).stream()
    
    deleted_count = 0
    batch = db.batch()
    
    for doc in docs:
        batch.delete(doc.reference)
        deleted_count += 1
        
        # Firestore batch has a limit of 500 operations
        if deleted_count % 500 == 0:
            batch.commit()
            print(f"Deleted {deleted_count} documents so far...")
            batch = db.batch() # Start a new batch
            
    # Commit any remaining deletes
    if deleted_count > 0:
        batch.commit()
        
    print(f"\nDone. Successfully deleted {deleted_count} records from Firestore.")

if __name__ == "__main__":
    main()
