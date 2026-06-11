#!/usr/bin/env python3
"""
reconcile_and_import.py — Reconcile and import new records from an expanded Excel/CSV master file.

This script directly compares a "new" expanded Excel/CSV file with a "current"
Excel/CSV file (representing the current catalog state). It prints a side-by-side
reconciliation table showing counts per letter, lists the newly added records,
and safely imports only the new ones into Firestore.

Usage:
    # Dry-run: reconcile and list discrepancies/new records
    python reconcile_and_import.py --current recordsWithSUMM.xlsx --new new_expanded.xlsx
    
    # Import: append the missing records directly into Firestore
    python reconcile_and_import.py --current recordsWithSUMM.xlsx --new new_expanded.xlsx --commit
"""

import os
import sys
import argparse
import json
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# Add local path to import project modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import record_store
from auto_backup import rotate_and_backup


def clean_text(text) -> str:
    """Helper to strip and lowercase text for exact-match comparison."""
    if text is None or pd.isna(text):
        return ""
    return "".join(str(text).strip().lower().split())


def read_data_file(filepath: str) -> pd.DataFrame:
    """Reads either an Excel (.xlsx) or CSV (.csv) file cleanly into a DataFrame."""
    path = os.path.abspath(filepath)
    if not os.path.exists(path):
        print(f"Error: File not found at '{path}'")
        sys.exit(1)
        
    print(f"Reading '{filepath}'...")
    try:
        if filepath.lower().endswith(".xlsx"):
            return pd.read_excel(path, dtype=str)
        elif filepath.lower().endswith(".csv"):
            return pd.read_csv(path, dtype=str)
        else:
            print(f"Error: Unsupported file extension for '{filepath}'. Must be .xlsx or .csv")
            sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Compare two Excel/CSV files, report count discrepancies, and import new records."
    )
    parser.add_argument(
        "--current",
        default="records_full_headed.csv",
        help="Path to the current master dataset (default: records_full_headed.csv)"
    )
    parser.add_argument(
        "--new",
        required=True,
        help="Path to the new expanded dataset"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually import the missing records into Firestore"
    )
    args = parser.parse_args()

    # 1. Load both dataframes
    df_current = read_data_file(args.current)
    df_new = read_data_file(args.new)

    print(f"Loaded Current File: {len(df_current)} rows")
    print(f"Loaded New File:     {len(df_new)} rows\n")

    # 2. Pre-process rows to resolve 'id_letter'
    print("Processing index letters...")
    for df in [df_current, df_new]:
        letters = []
        for _, row in df.iterrows():
            row_dict = {
                "artist": row.get("artist", "") or "",
                "name": row.get("name", "") or "",
                "id_letter": row.get("id_letter", "") or "",
                "box": row.get("box", 1)
            }
            # process_record_fields extracts correct id_letter
            processed = record_store.process_record_fields(row_dict)
            letters.append(processed.get("id_letter", ""))
        df["resolved_letter"] = letters

    # 3. Compute count per letter
    current_counts = df_current["resolved_letter"].value_counts().to_dict()
    new_counts = df_new["resolved_letter"].value_counts().to_dict()

    # Get union of all letters
    all_letters = sorted(list(set(current_counts.keys()) | set(new_counts.keys())))

    print("\n" + "=" * 60)
    print("              ALPHABETICAL RECONCILIATION REPORT")
    print("=" * 60)
    print(f"{'Letter':<10} | {'Current Count':<15} | {'New Count':<15} | {'Difference':<12}")
    print("-" * 60)

    total_diff = 0
    for letter in all_letters:
        if not letter.strip():
            disp_letter = "[Empty]"
        else:
            disp_letter = letter

        cc = current_counts.get(letter, 0)
        nc = new_counts.get(letter, 0)
        diff = nc - cc
        total_diff += diff
        
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        print(f"{disp_letter:<10} | {cc:<15} | {nc:<15} | {diff_str:<12}")

    print("-" * 60)
    print(f"{'TOTAL':<10} | {len(df_current):<15} | {len(df_new):<15} | +{total_diff if total_diff > 0 else total_diff:<12}")
    print("=" * 60 + "\n")

    # 4. Identify specific missing records
    # Build exact-match lookup from the current file
    current_lookup = set()
    for _, row in df_current.iterrows():
        a = clean_text(row.get("artist"))
        n = clean_text(row.get("name"))
        if a or n:
            current_lookup.add((a, n))

    missing_records = []
    for idx, row in df_new.iterrows():
        a = clean_text(row.get("artist"))
        n = clean_text(row.get("name"))
        if (a, n) not in current_lookup:
            # Reconstruct clean dict representation of row
            rec = {
                "artist": str(row.get("artist", "")).strip() if not pd.isna(row.get("artist")) else "",
                "name": str(row.get("name", "")).strip() if not pd.isna(row.get("name")) else "",
                "id_letter": str(row.get("id_letter", "")).strip() if not pd.isna(row.get("id_letter")) else "",
                "box": int(row.get("box")) if (not pd.isna(row.get("box")) and str(row.get("box")).isdigit()) else 1,
                "notes": str(row.get("notes", "")).strip() if not pd.isna(row.get("notes")) else ""
            }
            if not rec["artist"] and not rec["name"]:
                continue
            missing_records.append((idx + 1, rec))

    if not missing_records:
        print("🎉 No missing records found! Both datasets are fully synchronized.")
        sys.exit(0)

    print(f"🔍 Found {len(missing_records)} records in '{args.new}' that are missing from '{args.current}':")
    for row_num, rec in missing_records[:50]:
        print(f"  Row {row_num:<4}: Artist: '{rec['artist']}' | Album: '{rec['name']}' (Box: {rec['box']})")
    
    if len(missing_records) > 50:
        print(f"  ... and {len(missing_records) - 50} more records.")

    # 5. Safe Firestore Import (if --commit is specified)
    if args.commit:
        sdk_key = "firebase-adminsdk.json"
        if not os.path.exists(sdk_key):
            print(f"\nError: Firestore service account key file '{sdk_key}' is missing in the project folder.")
            sys.exit(1)

        print(f"\nInitializing Firestore Connection via '{sdk_key}'...")
        if not firebase_admin._apps:
            cred = credentials.Certificate(sdk_key)
            firebase_admin.initialize_app(cred)
        db = firestore.client()

        print(f"\nImporting {len(missing_records)} new records into Firestore...")
        
        # Batch write
        BATCH_SIZE = 400
        count = 0
        imported_successfully = 0
        
        batch = db.batch()
        for _, rec in missing_records:
            # process_record_fields handles hebrew-digit conversion and sorting_key generation
            processed_rec = record_store.process_record_fields(rec)
            
            # Write to Firestore
            doc_ref = db.collection(record_store.COLLECTION).document()
            batch.set(doc_ref, processed_rec)
            count += 1
            imported_successfully += 1
            
            if count >= BATCH_SIZE:
                print(f"  Batch committed: {imported_successfully}/{len(missing_records)} records...")
                batch.commit()
                batch = db.batch()
                count = 0
                
        if count > 0:
            print(f"  Final Batch committed: {imported_successfully}/{len(missing_records)} records...")
            batch.commit()

        print(f"\n✅ Success! Imported {imported_successfully} records into Firestore.")
        
        # Trigger rotating backup to Drive
        print("\nTriggering rotating backup to Google Drive...")
        try:
            # Read backup settings from local credentials
            with open(sdk_key) as f:
                creds_dict = json.load(f)
            # Run rotate_and_backup synchronously for verification
            rotate_and_backup(creds_dict)
            print("✓ Rotating backup completed successfully.")
        except Exception as e:
            print(f"⚠ Warning: Rotating backup failed: {e}")
            
        print("\nNote: Make sure to clear the dashboard cache on Streamlit Cloud to see the new records immediately.")
    else:
        print(f"\nTo import these {len(missing_records)} records into Firestore, rerun this command with the '--commit' flag:")
        print(f"  python reconcile_and_import.py --current {args.current} --new {args.new} --commit")


if __name__ == "__main__":
    main()
