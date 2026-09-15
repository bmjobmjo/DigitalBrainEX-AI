import os
import sys
import json
import subprocess
import urllib.request
import urllib.parse

REPO = "bmjobmjo/DigitalBrainEX-AI"
TAG = "v2.1.0"
TITLE = "DigitalBrainEX AI v2.1.0"

RELEASE_NOTES = """## DigitalBrainEX AI v2.1.0 Release Notes

### 🚀 Highlights & New Features

- **Single Instance Application (Singleton Protection)**:
  - Enforced OS-level Windows Named Mutex (`Global\\DigitalBrainEX_AI_Mutex_...`) ensuring only one instance runs at a time.
  - Implemented high-speed local IPC (`QLocalServer`/`QLocalSocket`) so launching a duplicate app instance or shortcut automatically unminimizes and brings the existing application window to the active foreground.

- **AskMe Module Crash Fix**:
  - Resolved application crash when clicking the "Configure in Settings" button in the AskMe assistant.
  - Added seamless cross-module tab routing directly into the GenAI configuration tab.

- **Multi-Term Search Support**:
  - Enabled multi-keyword search with `+` sign delimiter (e.g. `meeting + quarterly`), returning entries containing all specified terms.

- **Automated Startup Database Backup**:
  - Verified and enhanced automated daily timestamped SQLite backups on startup.

- **Wellness & Health Reminders**:
  - Fixed recurring timer triggers for hydration and sedentary alerts so reminders reliably repeat on schedule.
  - Added live "Next reminder in X minutes (HH:MM)" indicator directly in the Settings panel.

- **Secret Vault & Google Drive File Open**:
  - Fixed edit/view modal crash in the Secret Vault.
  - Restored Google Drive document open handling on double-click.

- **Database & Storage Optimization**:
  - Cleaned up orphan embedding records and legacy text fragments.
  - Executed SQLite `VACUUM` for optimized startup performance and reduced file size.

---

### 📦 Included Release Binaries
- `DigitalBrainEX.exe` - Portable standalone single-file Windows executable (no installation required).
- `DigitalBrainEX_Setup.exe` - Windows Installer wizard with desktop/Start Menu shortcuts and clean directory initialization.

---
**Full Changelog**: https://github.com/bmjobmjo/DigitalBrainEX-AI/compare/v2.0.0...v2.1.0
"""

def get_token():
    p = subprocess.Popen(
        ["C:/Espressif/tools/idf-git/2.44.0/mingw64/bin/git-credential-manager.exe", "get"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = p.communicate(input="protocol=https\nhost=github.com\n")
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    return None

def api_request(url, token, data=None, method="GET", content_type="application/json"):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "DigitalBrainEX-Release-Script",
        "Accept": "application/vnd.github.v3+json"
    }
    if content_type:
        headers["Content-Type"] = content_type

    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode("utf-8")
        elif isinstance(data, (bytes, bytearray)):
            body = data
        else:
            body = str(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read()
            if resp.status == 204 or not resp_body:
                return None
            return json.loads(resp_body.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        print(f"HTTP Error {e.code} on {url}: {err_msg}")
        raise

def main():
    token = get_token()
    if not token:
        print("ERROR: Failed to retrieve GitHub token from Git Credential Manager")
        sys.exit(1)
    print("Successfully retrieved GitHub token.")

    # Check if release already exists
    release = None
    try:
        release = api_request(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}", token)
        print(f"Found existing release for {TAG} (ID: {release['id']})")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"No existing release for {TAG}. Creating new release...")
        else:
            raise

    if not release:
        payload = {
            "tag_name": TAG,
            "target_commitish": "main",
            "name": TITLE,
            "body": RELEASE_NOTES,
            "draft": False,
            "prerelease": False
        }
        release = api_request(f"https://api.github.com/repos/{REPO}/releases", token, data=payload, method="POST")
        print(f"Release created successfully! (ID: {release['id']})")

    release_id = release["id"]
    existing_assets = {a["name"]: a["id"] for a in release.get("assets", [])}

    # Files to upload
    dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")
    files_to_upload = [
        os.path.join(dist_dir, "DigitalBrainEX.exe"),
        os.path.join(dist_dir, "DigitalBrainEX_Setup.exe")
    ]

    for file_path in files_to_upload:
        if not os.path.exists(file_path):
            print(f"ERROR: File not found: {file_path}")
            continue

        file_name = os.path.basename(file_path)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"\nProcessing asset: {file_name} ({file_size_mb:.2f} MB)...")

        # If asset already exists, delete it first
        if file_name in existing_assets:
            asset_id = existing_assets[file_name]
            print(f"Deleting existing asset ID {asset_id} ({file_name})...")
            api_request(f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}", token, method="DELETE")
            print("Deleted old asset.")

        # Upload asset
        upload_url = f"https://uploads.github.com/repos/{REPO}/releases/{release_id}/assets?name={urllib.parse.quote(file_name)}"
        print(f"Uploading {file_name} to GitHub Releases...")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        uploaded = api_request(upload_url, token, data=file_bytes, method="POST", content_type="application/octet-stream")
        print(f"Successfully uploaded: {file_name} -> {uploaded.get('browser_download_url')}")

    print("\n=== RELEASE v2.1.0 PUBLISHED SUCCESSFULLY ===")
    print(f"Release URL: {release.get('html_url')}")

if __name__ == "__main__":
    main()
