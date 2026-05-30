"""
drive_backup.py — Google Drive backup with rotating 3-file limit.

Usage (called from app.py after any Firestore mutation):
    from drive_backup import upload_backup_to_drive
    upload_backup_to_drive(df, st.secrets["firebase"], st.secrets["gdrive_backup_folder_id"])

Rotation policy:
  - Files are named  records_backup_YYYYMMDD_HHMMSS.csv
  - Only files matching that pattern are counted / deleted
  - If the folder already contains 3+ backups, the oldest (by createdTime)
    is deleted before the new one is uploaded.
  - Net result: the folder always holds exactly the 3 most recent snapshots.
"""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BACKUP_FILENAME_RE = re.compile(r"^records_backup_\d{8}_\d{6}\.csv$")
_SCOPES = ["https://www.googleapis.com/auth/drive"]
_MAX_BACKUPS = 3


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def build_drive_service(firebase_secrets: dict):
    """Build an authenticated Drive service from Firebase service account secrets."""
    creds = service_account.Credentials.from_service_account_info(
        dict(firebase_secrets),
        scopes=_SCOPES,
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _list_backups(service, folder_id: str) -> list[dict]:
    """
    Return a list of backup file metadata dicts, sorted oldest → newest.
    Each dict has keys: id, name, createdTime.
    """
    query = (
        f"'{folder_id}' in parents "
        f"and mimeType = 'text/csv' "
        f"and trashed = false"
    )
    results = (
        service.files()
        .list(
            q=query,
            fields="files(id, name, createdTime)",
            orderBy="createdTime asc",
            pageSize=50,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    all_files = results.get("files", [])
    # Filter to only our pattern so we never accidentally delete other CSVs
    return [f for f in all_files if _BACKUP_FILENAME_RE.match(f["name"])]


def _delete_file(service, file_id: str) -> None:
    """Permanently delete a Drive file by ID."""
    service.files().delete(fileId=file_id, supportsAllDrives=True).execute()


def _upload_csv(service, df: pd.DataFrame, folder_id: str, filename: str) -> str:
    """Upload a DataFrame as a CSV to the given Drive folder. Returns new file ID."""
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upload_backup_to_drive(
    df: pd.DataFrame,
    firebase_secrets,
    folder_id: str,
) -> None:
    """
    Back up ``df`` to Google Drive, enforcing a 3-file rotation.

    Parameters
    ----------
    df:
        The full records DataFrame to back up.
    firebase_secrets:
        ``st.secrets["firebase"]`` — the service account credentials dict.
    folder_id:
        Google Drive folder ID (from ``st.secrets["gdrive_backup_folder_id"]``).
    """
    # Explicit conversion ensures no Streamlit AttrDict remnants reach the auth library
    service = build_drive_service(dict(firebase_secrets))

    # 1. List existing backups (oldest first)
    existing = _list_backups(service, folder_id)

    # 2. Delete oldest files until we're under the limit (leaving room for 1 new)
    while len(existing) >= _MAX_BACKUPS:
        oldest = existing.pop(0)
        _delete_file(service, oldest["id"])

    # 3. Generate timestamped filename using UTC time
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"records_backup_{timestamp}.csv"

    # 4. Upload the new backup
    _upload_csv(service, df, folder_id, filename)
