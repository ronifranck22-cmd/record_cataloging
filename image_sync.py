"""
image_sync.py — Album cover sync: Discogs → Google Drive → Firestore.

Reusable functions
------------------
sync_single_record(db, drive_service, doc_id, image_url, covers_folder_id)
    Download one image and update its Firestore record.

run_bulk_sync(db, drive_service, covers_folder_id, limit=None)
    Batch-process all un-synced records (skips already-synced ones).

CLI usage
---------
    # Activate venv first, then:
    python image_sync.py --folder-id YOUR_COVERS_FOLDER_ID
    python image_sync.py --folder-id YOUR_COVERS_FOLDER_ID --limit 10
"""

from __future__ import annotations

import io
import time
import argparse

import requests
from googleapiclient.http import MediaIoBaseUpload

import record_store
from drive_backup import build_drive_service


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# A realistic browser User-Agent so Discogs CDN doesn't 403 us.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.discogs.com/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

_DRIVE_PUBLIC_URL = "https://drive.google.com/uc?export=view&id={file_id}"

# Polite delay between Discogs requests (seconds)
_DELAY = 1.2


# ---------------------------------------------------------------------------
# Core sync function (one record)
# ---------------------------------------------------------------------------

def sync_single_record(
    db,
    drive_service,
    doc_id: str,
    image_url: str,
    covers_folder_id: str,
) -> str | None:
    """
    Download *image_url* from Discogs, upload it to the Drive covers folder,
    make it publicly readable, then update Firestore with the new URL and
    set ``image_synced = True``.

    Returns the new public Drive URL on success, or ``None`` on any failure.
    The function is intentionally non-raising — callers can treat None as a
    soft failure and move on.
    """
    try:
        # 1. Download image bytes from Discogs
        resp = requests.get(image_url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  ⚠  HTTP {resp.status_code} for {doc_id} — skipping")
            return None

        content_type = resp.headers.get("Content-Type", "image/jpeg")
        ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
        filename = f"{doc_id}.{ext}"
        image_bytes = resp.content

        # 2. Upload to Drive covers folder
        file_metadata = {
            "name": filename,
            "parents": [covers_folder_id],
            "mimeType": content_type,
        }
        media = MediaIoBaseUpload(
            io.BytesIO(image_bytes),
            mimetype=content_type,
            resumable=False,
        )
        created = (
            drive_service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            )
            .execute()
        )
        file_id = created["id"]

        # 3. Make the file publicly readable (anyone with link)
        drive_service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        new_url = _DRIVE_PUBLIC_URL.format(file_id=file_id)

        # 4. Update Firestore record
        db.collection(record_store.COLLECTION).document(doc_id).update(
            {"image_url": new_url, "image_synced": True}
        )

        return new_url

    except Exception as exc:
        print(f"  ✗  Error syncing {doc_id}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Bulk sync (all un-synced records)
# ---------------------------------------------------------------------------

def run_bulk_sync(
    db,
    drive_service,
    covers_folder_id: str,
    limit: int | None = None,
) -> None:
    """
    Scan Firestore for records that have an ``image_url`` but no
    ``image_synced = True`` flag, then sync each one.

    Safe to interrupt and re-run — already-synced records are skipped.
    """
    print("🔍  Fetching un-synced records from Firestore…")
    records = record_store.get_unsynced(db)

    if not records:
        print("✅  All records are already synced. Nothing to do.")
        return

    if limit:
        records = records[:limit]

    total = len(records)
    print(f"📦  Found {total} record(s) to sync.\n")

    ok = 0
    fail = 0

    for i, rec in enumerate(records, start=1):
        doc_id = rec["id"]
        image_url = rec.get("image_url", "")
        artist = rec.get("artist", "")
        name = rec.get("name", "")
        label = f"{artist} — {name}"

        print(f"[{i:4d}/{total}]  {label[:60]:<60}", end="  ", flush=True)

        new_url = sync_single_record(db, drive_service, doc_id, image_url, covers_folder_id)
        if new_url:
            print("✓")
            ok += 1
        else:
            print("✗  (see error above)")
            fail += 1

        # Respect Discogs CDN rate limits
        if i < total:
            time.sleep(_DELAY)

    print(f"\n✅  Done — {ok} synced, {fail} failed out of {total} total.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import firebase_admin
    from firebase_admin import credentials as _fb_creds, firestore as _fb_firestore

    parser = argparse.ArgumentParser(
        description="Sync album cover images from Discogs to Google Drive."
    )
    parser.add_argument(
        "--folder-id",
        required=True,
        help="Google Drive folder ID for the 'Records_Covers' subfolder.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of records to sync (omit for all).",
    )
    args = parser.parse_args()

    # Load Firebase service account from the local JSON file (bypasses st.secrets)
    with open("firebase-adminsdk.json") as f:
        creds_dict = json.load(f)

    # Initialize Firebase directly — no Streamlit context needed
    if not firebase_admin._apps:
        firebase_admin.initialize_app(_fb_creds.Certificate(creds_dict))
    db_client = _fb_firestore.client()

    drive_svc = build_drive_service(creds_dict)

    run_bulk_sync(db_client, drive_svc, args.folder_id, limit=args.limit)

