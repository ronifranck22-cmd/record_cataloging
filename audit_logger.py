"""
audit_logger.py — Non-blocking background audit logging utility for database mutations.

Saves a log of mutations to audit_log.xlsx in a Google Drive folder and keeps a local copy.
"""

from __future__ import annotations

import io
import os
import threading
from datetime import datetime
import pandas as pd

from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from drive_backup import build_drive_service

# Constants
_AUDIT_LOG_FILENAME = "audit_log.xlsx"
_COLUMNS = ["Timestamp", "Action Type", "Record ID", "Artist", "Album", "Notes"]
_EXCEL_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def log_mutation(
    action_type: str,
    record_id: str,
    artist: str,
    album: str,
    notes: str,
    firebase_secrets: dict = None,
    folder_id: str = None
) -> None:
    """
    Spawn a background daemon thread to log a database mutation.
    This guarantees that the log operation is non-intrusive and does not
    block the Streamlit UI or fail/crash the application.
    """
    try:
        t = threading.Thread(
            target=_sync_audit_log,
            args=(action_type, record_id, artist, album, notes, firebase_secrets, folder_id),
            daemon=True
        )
        t.start()
    except Exception as e:
        print(f"Audit Log Error: Failed to spawn logger thread: {e}", flush=True)

def get_valid_folder_id(service, requested_folder_id: str) -> str:
    """
    Checks if requested_folder_id is valid. If not, searches for a folder named
    'Records_Backups' in Google Drive. If that is also missing, creates it.
    """
    if requested_folder_id:
        try:
            service.files().get(fileId=requested_folder_id, supportsAllDrives=True).execute()
            return requested_folder_id
        except Exception as e:
            print(f"Audit Log: Folder ID '{requested_folder_id}' is invalid or inaccessible: {e}. Searching for 'Records_Backups' folder...", flush=True)

    try:
        query = "name = 'Records_Backups' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            spaces="drive",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get("files", [])
        if files:
            print(f"Audit Log: Found existing folder 'Records_Backups' with ID: {files[0]['id']}", flush=True)
            return files[0]["id"]
            
        # Create folder if it doesn't exist
        file_metadata = {
            "name": "Records_Backups",
            "mimeType": "application/vnd.google-apps.folder"
        }
        folder = service.files().create(
            body=file_metadata,
            fields="id",
            supportsAllDrives=True
        ).execute()
        new_fid = folder.get("id")
        print(f"Audit Log: Created new 'Records_Backups' folder with ID: {new_fid}", flush=True)
        return new_fid
    except Exception as e:
        print(f"Audit Log Error: Failed to resolve backup folder dynamically: {e}", flush=True)
        # Final fallback to working covers folder if possible
        return "17_IBjldm6rNhi5vdb_c8QGwgqnza3WP5"

def _sync_audit_log(
    action_type: str,
    record_id: str,
    artist: str,
    album: str,
    notes: str,
    firebase_secrets: dict | None,
    folder_id: str | None
) -> None:
    """
    Internal thread worker that downloads the existing audit log from Google Drive,
    appends the new log row, saves it locally, and uploads it back to Google Drive.
    """
    print(f"Audit Log: Syncing {action_type} for ID: {record_id}...", flush=True)
    
    # Force string conversion to prevent openpyxl / pandas serialization errors
    record_id = str(record_id or "").strip()
    artist = str(artist or "").strip()
    album = str(album or "").strip()
    notes = str(notes or "").strip()
    
    # 1. Resolve folder ID from Streamlit secrets if not provided
    if not folder_id:
        try:
            import streamlit as st
            folder_id = st.secrets.get("gdrive_backup_folder_id", "")
        except Exception:
            pass
            
    if not folder_id:
        print("Audit Log Warning: No Google Drive folder ID resolved. Logging locally only.", flush=True)
        
    df = None
    drive_service = None
    existing_file_id = None
    
    # 2. Try authenticating and downloading from Google Drive
    if folder_id or firebase_secrets:
        try:
            # Explicitly parse/convert firebase secrets dict
            secrets_dict = dict(firebase_secrets) if firebase_secrets else None
            if not secrets_dict:
                try:
                    import streamlit as st
                    if "firebase" in st.secrets:
                        secrets_dict = dict(st.secrets["firebase"])
                except Exception:
                    pass
            
            drive_service = build_drive_service(secrets_dict)
            folder_id = get_valid_folder_id(drive_service, folder_id)
            
            # Query for the file in the designated backups folder
            query = f"'{folder_id}' in parents and name = '{_AUDIT_LOG_FILENAME}' and trashed = false"
            results = drive_service.files().list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get("files", [])
            if files:
                existing_file_id = files[0]["id"]
                
                # Download file content to buffer
                request = drive_service.files().get_media(fileId=existing_file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                fh.seek(0)
                
                # Load with pandas
                df = pd.read_excel(fh, engine='openpyxl')
                print("Audit Log: Successfully downloaded existing log from Google Drive.", flush=True)
        except Exception as e:
            print(f"Audit Log Warning: Failed to retrieve file from Google Drive: {e}. Falling back to local copy.", flush=True)

    # 3. Fallback: load local copy if Drive retrieval failed/was skipped
    if df is None:
        if os.path.exists(_AUDIT_LOG_FILENAME):
            try:
                df = pd.read_excel(_AUDIT_LOG_FILENAME, engine='openpyxl')
                print("Audit Log: Successfully loaded local audit_log.xlsx file.", flush=True)
            except Exception as e:
                print(f"Audit Log Warning: Failed to read local audit_log.xlsx: {e}", flush=True)
                
    # 4. Initialize empty DataFrame if no file exists anywhere
    if df is None:
        df = pd.DataFrame(columns=_COLUMNS)
        print("Audit Log: Initialized a new audit log DataFrame.", flush=True)

    # 5. Append new audit log row
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = {
        "Timestamp": timestamp_str,
        "Action Type": action_type,
        "Record ID": record_id,
        "Artist": artist,
        "Album": album,
        "Notes": notes
    }
    
    # Check if there is any mismatch in column order/names
    for col in _COLUMNS:
        if col not in df.columns:
            df[col] = None
            
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # 6. Save updated log locally (failsafe & cache)
    try:
        df.to_excel(_AUDIT_LOG_FILENAME, index=False, engine='openpyxl')
        print(f"Audit Log: Local copy updated successfully with action '{action_type}'.", flush=True)
    except Exception as e:
        print(f"Audit Log Error: Failed to write local copy: {e}", flush=True)

    # 7. Upload / Update on Google Drive
    if drive_service and folder_id:
        try:
            # Save the updated Excel file in memory
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_bytes = excel_buffer.getvalue()
            
            media = MediaIoBaseUpload(
                io.BytesIO(excel_bytes),
                mimetype=_EXCEL_MIMETYPE,
                resumable=False
            )
            
            if existing_file_id:
                # Update existing file content
                drive_service.files().update(
                    fileId=existing_file_id,
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                print("Audit Log: Successfully updated existing audit_log.xlsx on Google Drive.", flush=True)
            else:
                # Create a new file in the backup folder
                file_metadata = {
                    "name": _AUDIT_LOG_FILENAME,
                    "parents": [folder_id],
                    "mimeType": _EXCEL_MIMETYPE
                }
                drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                print("Audit Log: Successfully created and uploaded new audit_log.xlsx to Google Drive.", flush=True)
        except Exception as e:
            print(f"Audit Log Error: Failed to upload updated log to Google Drive: {e}", flush=True)
