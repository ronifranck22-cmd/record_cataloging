#!/usr/bin/env python3
"""
image_enricher.py — Album cover search and sync for records missing covers.

Scans Firestore for records without an image_url, searches Discogs & Stereo-Ve-Mono,
and uploads matches to Google Drive and updates Firestore.

Usage:
    # Dry-run: search and print matches
    python image_enricher.py
    
    # Commit: search, upload to Drive, and commit to Firestore
    python image_enricher.py --commit --folder-id YOUR_COVERS_FOLDER_ID
"""

import os
import sys
import argparse
import time
import json
import pandas as pd
import firebase_admin
from firebase_admin import credentials as fb_creds, firestore as fb_firestore

# Add local path to import project modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import enrich_records
import image_sync
from drive_backup import build_drive_service

def main():
    parser = argparse.ArgumentParser(
        description="Search and sync cover images for Firestore records missing them."
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually sync found images to Google Drive and update Firestore"
    )
    parser.add_argument(
        "--folder-id",
        help="Google Drive folder ID for 'Records_Covers' (required for --commit)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of records to process"
    )
    args = parser.parse_args()

    if args.commit and not args.folder_id:
        # Try to parse folder-id from secrets.toml if available and not placeholder
        secrets_path = os.path.join(".streamlit", "secrets.toml")
        if os.path.exists(secrets_path):
            try:
                with open(secrets_path) as sf:
                    for line in sf:
                        if "gdrive_covers_folder_id" in line:
                            parts = line.split("=")
                            if len(parts) > 1:
                                fid = parts[1].strip().replace('"', '').replace("'", "")
                                if fid and "YOUR" not in fid:
                                    args.folder_id = fid
                                    break
            except Exception:
                pass
                
        if not args.folder_id:
            print("Error: --folder-id is required when running in --commit mode.")
            print("Example: python image_enricher.py --commit --folder-id YOUR_FOLDER_ID")
            sys.exit(1)

    sdk_key = "firebase-adminsdk.json"
    if not os.path.exists(sdk_key):
        print(f"Error: Firestore service account key file '{sdk_key}' is missing in the project folder.")
        sys.exit(1)

    # Initialize Firestore
    if not firebase_admin._apps:
        firebase_admin.initialize_app(fb_creds.Certificate(sdk_key))
    db = fb_firestore.client()

    print("Fetching all records from Firestore...")
    docs = list(db.collection("records").stream())
    print(f"Total records in database: {len(docs)}")

    # Filter records that lack an image_url
    records_to_enrich = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        img_url = str(data.get("image_url", "") or "").strip()
        
        # We process it if it's missing, empty, or set to "Not Found"
        if not img_url or img_url.lower() == "not found":
            records_to_enrich.append(data)

    print(f"Found {len(records_to_enrich)} records without cover images.")
    if not records_to_enrich:
        print("🎉 All records already have cover images associated!")
        sys.exit(0)

    if args.limit:
        records_to_enrich = records_to_enrich[:args.limit]
        print(f"Limiting to first {len(records_to_enrich)} records.")

    # Build Drive service if committing
    drive_svc = None
    if args.commit:
        with open(sdk_key) as f:
            creds_dict = json.load(f)
        drive_svc = build_drive_service(creds_dict)

    found_count = 0
    synced_count = 0

    print("\nStarting search & enrichment process...\n")
    for i, rec in enumerate(records_to_enrich, start=1):
        artist = str(rec.get("artist", "") or "").strip()
        name = str(rec.get("name", "") or "").strip()
        doc_id = rec["id"]
        
        print(f"[{i}/{len(records_to_enrich)}] Searching cover for: '{artist}' — '{name}'")
        
        # Clean spelling typos using helper
        clean_artist = enrich_records.apply_typo_fix(artist)
        
        # Search Discogs & Stereo-Ve-Mono
        img, price = enrich_records.get_discogs_data(clean_artist, name)
        if not img:
            img = enrich_records.scrape_stereo_ve_mono(artist, name)
            
        if img:
            found_count += 1
            print(f"  ✅ Match found! Image URL: {img}")
            
            if args.commit:
                print("  Uploading to Google Drive and updating Firestore...")
                new_url = image_sync.sync_single_record(
                    db,
                    drive_svc,
                    doc_id,
                    img,
                    args.folder_id
                )
                if new_url:
                    print("  ✓ Successfully synced to Google Drive and Firestore!")
                    synced_count += 1
                else:
                    print("  ✗ Sync failed.")
        else:
            print("  ❌ No match found.")
            if args.commit:
                # Mark as 'Not Found' in Firestore to avoid search loops
                db.collection("records").document(doc_id).update({"image_url": "Not Found"})
        
        # Delay to be polite to APIs
        if i < len(records_to_enrich):
            time.sleep(1.5)

    print("\n" + "="*50)
    print("ENRICHMENT SUMMARY")
    print("="*50)
    print(f"Processed: {len(records_to_enrich)}")
    print(f"Covers Found: {found_count}")
    if args.commit:
        print(f"Successfully Synced: {synced_count}")
    else:
        print("Note: Run with '--commit --folder-id YOUR_COVERS_FOLDER_ID' to save the covers.")
    print("="*50)

if __name__ == "__main__":
    main()
