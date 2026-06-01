"""
auto_backup.py — Invisible background backup system with 3-file rotation policy.

This module provides the rotate_and_backup() function which is called in a
daemon thread to backup the Firestore 'records' collection to a Google Drive
folder named 'Records_Backups'.
"""

from __future__ import annotations

import io
import re
import os
from datetime import datetime, timezone
import pandas as pd

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from db_client import get_db
import record_store

# Constants
_BACKUP_FILENAME_RE = re.compile(r"^records_backup_\d{8}_\d{6}\.csv$")
_SCOPES = ["https://www.googleapis.com/auth/drive"]
_MAX_BACKUPS = 3

def get_non_interactive_creds(firebase_secrets: dict = None) -> Credentials | service_account.Credentials | None:
    """Load credentials non-interactively to avoid blocking background threads."""
    creds = None
    
    # 1. Try authorized token.json
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", _SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            if creds and creds.valid:
                return creds
        except Exception as e:
            print(f"Auto-Backup: Error loading or refreshing token.json: {e}")
            
    # 2. Try Firebase service account secrets passed in
    if firebase_secrets:
        try:
            return service_account.Credentials.from_service_account_info(
                dict(firebase_secrets),
                scopes=_SCOPES,
            )
        except Exception as e:
            print(f"Auto-Backup: Error loading service account credentials: {e}")

    # 3. Fallback to Streamlit secrets (gdrive_token)
    try:
        import streamlit as st
        if "gdrive_token" in st.secrets:
            token_info = dict(st.secrets["gdrive_token"])
            creds = Credentials.from_authorized_user_info(token_info, _SCOPES)
            if creds and creds.valid:
                return creds
    except Exception:
        pass
        
    return None

def build_drive_service(firebase_secrets: dict = None):
    """Build an authenticated Drive service using non-interactive credentials."""
    creds = get_non_interactive_creds(firebase_secrets)
    if not creds:
        raise ValueError("No valid credentials found (need token.json or service account info)")
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def get_or_create_backup_folder(service, folder_name: str = "Records_Backups") -> str:
    """Find or create the folder named 'Records_Backups' in Google Drive."""
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        spaces="drive",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    files = results.get("files", [])
    if files:
        return files[0]["id"]
        
    # Folder not found, create it
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    folder = service.files().create(
        body=file_metadata,
        fields="id",
        supportsAllDrives=True
    ).execute()
    return folder.get("id")

def _list_backups(service, folder_id: str) -> list[dict]:
    """List all CSV backups in the backup folder, sorted by creation time (oldest first)."""
    query = f"'{folder_id}' in parents and mimeType = 'text/csv' and trashed = false"
    results = (
        service.files()
        .list(
            q=query,
            fields="files(id, name, createdTime)",
            orderBy="createdTime asc",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    all_files = results.get("files", [])
    # Return only files that match the expected backup filename format
    return [f for f in all_files if _BACKUP_FILENAME_RE.match(f["name"])]

def _delete_file(service, file_id: str) -> None:
    """Delete a Drive file by ID."""
    service.files().delete(fileId=file_id, supportsAllDrives=True).execute()

def _upload_csv(service, df: pd.DataFrame, folder_id: str, filename: str) -> str:
    """Upload a Pandas DataFrame as a CSV file to the given Drive folder."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    file_metadata = {
        "name": filename,
        "parents": [folder_id],
        "mimeType": "text/csv",
    }
    media = MediaIoBaseUpload(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        resumable=False,
    )
    file = (
        service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    return file.get("id")

def rotate_and_backup(firebase_secrets: dict = None) -> None:
    """
    Fetch all Firestore records, convert to CSV, upload to the
    'Records_Backups' Google Drive folder, and keep only the 3 newest backups.
    
    This function is completely self-contained and fails silently (with print logging)
    to avoid blocking the main user workflow or throwing UI errors.
    """
    print("Auto-Backup: rotate_and_backup background task triggered.")
    try:
        # 1. Fetch entire Firestore collection
        db = get_db()
        df = record_store.get_all(db, limit=None)
        
        # 2. Authenticate Google Drive Service
        service = build_drive_service(firebase_secrets)
        
        # 3. Locate or create backup folder
        folder_id = get_or_create_backup_folder(service, "Records_Backups")
        
        # 4. List and rotate existing files (limit to keeping at most 2, so the new one makes 3)
        existing = _list_backups(service, folder_id)
        while len(existing) >= _MAX_BACKUPS:
            oldest = existing.pop(0)
            _delete_file(service, oldest["id"])
            
        # 5. Generate timestamped filename and upload new CSV
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"records_backup_{timestamp}.csv"
        new_file_id = _upload_csv(service, df, folder_id, filename)
        
        print(f"Auto-Backup: Successfully backed up to Records_Backups/ {filename} (ID: {new_file_id})")
        
    except Exception as e:
        print(f"Auto-Backup Error: {e}")
