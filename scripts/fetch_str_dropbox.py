"""
fetch_str_dropbox.py

Downloads STR weekly and monthly Excel exports from Dropbox shared folder links.
Saves files to:
  data/str/weekly/   ← STR weekly (daily-grain) exports
  data/str/monthly/  ← STR monthly-grain exports

Requires env var: DROPBOX_ACCESS_TOKEN
  Get one at: https://www.dropbox.com/developers/apps
  → Create App → Full Dropbox scope → Generate access token

Usage:
  python scripts/fetch_str_dropbox.py
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent

WEEKLY_DIR = PROJECT_ROOT / "data" / "str" / "weekly"
MONTHLY_DIR = PROJECT_ROOT / "data" / "str" / "monthly"

# Dropbox shared folder links provided by STR.
# Each URL points directly to its subfolder — use with path="" for listing.
WEEKLY_FOLDER_URL = (
    "https://www.dropbox.com/scl/fo/ua6phm862g2dhlivuhhzh/ANKnc0sSWvtvF2TTcT4_j1w/2026"
    "?rlkey=mmhmwkgp0qcyoop3szrz8xtdx&dl=0"
)
MONTHLY_FOLDER_URL = (
    "https://www.dropbox.com/scl/fo/ua6phm862g2dhlivuhhzh/APCDmFO0BYYCJhG7y8cPLWk/2026/2026%20Monthly"
    "?rlkey=mmhmwkgp0qcyoop3szrz8xtdx&dl=0"
)
# Root URL used as the shared_link reference for file downloads
DROPBOX_ROOT_URL = (
    "https://www.dropbox.com/scl/fo/ua6phm862g2dhlivuhhzh"
    "?rlkey=mmhmwkgp0qcyoop3szrz8xtdx&dl=0"
)

DROPBOX_LIST_URL          = "https://api.dropboxapi.com/2/files/list_folder"
DROPBOX_LIST_CONTINUE_URL = "https://api.dropboxapi.com/2/files/list_folder/continue"
DROPBOX_DOWNLOAD_URL      = "https://content.dropboxapi.com/2/sharing/get_shared_link_file"


def get_token() -> str:
    token = os.environ.get("DROPBOX_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: DROPBOX_ACCESS_TOKEN environment variable not set.")
        print(
            "  1. Go to https://www.dropbox.com/developers/apps\n"
            "  2. Create an app (Full Dropbox access)\n"
            "  3. Generate an access token\n"
            "  4. export DROPBOX_ACCESS_TOKEN=<token>"
        )
        sys.exit(1)
    return token


def list_folder_files(token: str, folder_url: str) -> list[dict]:
    """List all .xlsx files in a Dropbox shared folder link."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "shared_link": {"url": folder_url},
        "path": "",
        "recursive": False,
    }

    all_entries = []
    cursor = None

    while True:
        if cursor:
            resp = requests.post(
                DROPBOX_LIST_CONTINUE_URL,
                headers=headers,
                json={"cursor": cursor},
                timeout=30,
            )
        else:
            resp = requests.post(
                DROPBOX_LIST_URL,
                headers=headers,
                json=body,
                timeout=30,
            )

        if resp.status_code != 200:
            print(f"ERROR listing folder: {resp.status_code} {resp.text[:300]}")
            return []

        data = resp.json()
        entries = data.get("entries", [])
        excel_entries = [
            e for e in entries
            if e.get(".tag") == "file" and e["name"].lower().endswith((".xlsx", ".xls"))
        ]
        all_entries.extend(excel_entries)

        if not data.get("has_more", False):
            break
        cursor = data.get("cursor")

    return all_entries


def download_file(token: str, file_path: str, dest_path: Path) -> bool:
    """Download a single file using its Dropbox path via files/download endpoint."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Dropbox-API-Arg": json.dumps({"path": file_path}),
    }

    for attempt in range(4):
        try:
            resp = requests.post(
                "https://content.dropboxapi.com/2/files/download",
                headers=headers,
                timeout=120,
                stream=True,
            )
            if resp.status_code == 200:
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True

            # Fallback: try sharing/get_shared_link_file with root URL + path
            print(f"  files/download failed ({resp.status_code}), trying shared link download...")
            break

        except requests.RequestException as e:
            print(f"  WARN: attempt {attempt+1} network error: {e}")
            if attempt < 3:
                time.sleep(2 ** attempt)

    return False


def download_file_via_shared_link(
    token: str, root_url: str, file_path: str, dest_path: Path
) -> bool:
    """Download using sharing/get_shared_link_file (requires sharing.read scope)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Dropbox-API-Arg": json.dumps({"url": root_url, "path": file_path}),
    }

    for attempt in range(4):
        try:
            resp = requests.post(
                DROPBOX_DOWNLOAD_URL,
                headers=headers,
                timeout=120,
                stream=True,
            )
            if resp.status_code == 200:
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True

            print(f"  WARN: attempt {attempt+1} HTTP {resp.status_code}: {resp.text[:200]}")
            if attempt < 3:
                time.sleep(2 ** attempt)

        except requests.RequestException as e:
            print(f"  WARN: attempt {attempt+1} network error: {e}")
            if attempt < 3:
                time.sleep(2 ** attempt)

    return False


def sync_folder(
    token: str, folder_url: str, local_dir: Path, label: str
) -> list[Path]:
    """List and download all .xlsx files from a Dropbox shared folder."""
    local_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[{label}] Listing files from Dropbox...")
    entries = list_folder_files(token, folder_url)

    if not entries:
        print(f"  No .xlsx files found.")
        return []

    print(f"  Found {len(entries)} .xlsx file(s):")
    for e in entries:
        print(f"    {e['name']}  ({e.get('size', 0):,} bytes)  path: {e.get('path_lower','?')}")

    downloaded = []
    for entry in entries:
        name = entry["name"]
        dest = local_dir / name
        file_path = entry.get("path_lower", f"/{name}")

        if dest.exists():
            remote_modified = entry.get("server_modified", "")
            local_modified = datetime.fromtimestamp(dest.stat().st_mtime).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            if remote_modified <= local_modified:
                print(f"  SKIP (up to date): {name}")
                downloaded.append(dest)
                continue

        print(f"  Downloading: {name} ...", end=" ", flush=True)
        # Try files/download first (needs only files.content.read); fall back to shared link
        ok = download_file(token, file_path, dest)
        if not ok:
            ok = download_file_via_shared_link(token, DROPBOX_ROOT_URL, file_path, dest)

        if ok:
            print("OK")
            downloaded.append(dest)
        else:
            print("FAILED")

    return downloaded


def main():
    token = get_token()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] fetch_str_dropbox starting")

    weekly_files = sync_folder(token, WEEKLY_FOLDER_URL, WEEKLY_DIR, "WEEKLY/DAILY")
    monthly_files = sync_folder(token, MONTHLY_FOLDER_URL, MONTHLY_DIR, "MONTHLY")

    print(f"\nSummary:")
    print(f"  Weekly files:  {len(weekly_files)} in {WEEKLY_DIR}")
    print(f"  Monthly files: {len(monthly_files)} in {MONTHLY_DIR}")
    print(f"\nNext: python scripts/run_pipeline.py")


if __name__ == "__main__":
    main()
