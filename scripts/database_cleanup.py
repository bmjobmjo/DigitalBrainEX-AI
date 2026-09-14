"""
Database and Storage Cleanup Script for DigitalBrainEX AI.

Performs:
1. Online SQLite backup of DevDiary-10-09-2026.db3 (to database/ and LocalDocFolder/).
2. Zip archive of all legacy text fragments (*_full.txt, *.vect, UrlsEmbeddings/).
3. Detection and deletion of missing local document entries, exporting missing_local_documents.csv.
4. Verification and deletion of dead/inaccessible Google Drive URLs, exporting unaccessible_google_docs.csv.
5. Removal of all old embeddings from Embeddings and Embeddings_backup tables.
6. Resetting of EmbeddingStatus to 'PENDING' for all remaining valid documents.
7. Deletion of all legacy text fragment files and UrlsEmbeddings directory.
8. Database VACUUM and PRAGMA optimize to reclaim disk space.
"""

import os
import sys
import time
import csv
import shutil
import zipfile
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# Paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "database", "DevDiary-10-09-2026.db3")
DOC_FOLDER = r"D:\DBX\LocalDocFolder"
REPORTS_DIR = os.path.join(REPO_ROOT, "cleanup_reports")
LOCAL_APP_DB = os.path.expandvars(r"%LOCALAPPDATA%\DigitalBrainEX\database\DevDiary-10-09-2026.db3")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def step1_backup_database(timestamp_str: str) -> tuple[str, str]:
    log("=== STEP 1: Creating Database Backups ===")
    os.makedirs(os.path.join(REPO_ROOT, "database"), exist_ok=True)
    os.makedirs(DOC_FOLDER, exist_ok=True)

    backup1 = os.path.join(REPO_ROOT, "database", f"DevDiary-PreCleanup-Backup-{timestamp_str}.db3")
    backup2 = os.path.join(DOC_FOLDER, f"DevDiary-PreCleanup-Backup-{timestamp_str}.db3")

    src_conn = sqlite3.connect(DB_PATH)
    try:
        # Ensure WAL journal is checkpointed
        src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        # Online backup to backup1
        dst_conn1 = sqlite3.connect(backup1)
        with dst_conn1:
            src_conn.backup(dst_conn1)
        dst_conn1.close()
        log(f"Database backup created: {backup1} ({os.path.getsize(backup1):,} bytes)")

        # Online backup to backup2
        dst_conn2 = sqlite3.connect(backup2)
        with dst_conn2:
            src_conn.backup(dst_conn2)
        dst_conn2.close()
        log(f"Secondary database backup created: {backup2} ({os.path.getsize(backup2):,} bytes)")
    finally:
        src_conn.close()

    return backup1, backup2


def step2_backup_text_fragments(timestamp_str: str) -> str:
    log("=== STEP 2: Archiving Legacy Text Fragments to Zip ===")
    zip_path = os.path.join(DOC_FOLDER, f"text_fragments_backup_{timestamp_str}.zip")

    fragment_files = []
    # Find all *_full.txt and *.vect in DOC_FOLDER
    for root, dirs, files in os.walk(DOC_FOLDER):
        for f in files:
            if f.endswith("_full.txt") or f.endswith(".vect") or "UrlsEmbeddings" in root:
                fragment_files.append(os.path.join(root, f))

    log(f"Found {len(fragment_files):,} legacy text fragment / embedding files to archive.")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in fragment_files:
            rel_name = os.path.relpath(fpath, DOC_FOLDER)
            zf.write(fpath, arcname=rel_name)

    log(f"Archived {len(fragment_files):,} files into: {zip_path} ({os.path.getsize(zip_path):,} bytes)")
    return zip_path


def step3_missing_local_documents(conn: sqlite3.Connection) -> list[int]:
    log("=== STEP 3: Checking Missing Local Documents ===")
    report_file_1 = os.path.join(REPORTS_DIR, "missing_local_documents.csv")
    if os.path.exists(report_file_1) and os.path.getsize(report_file_1) > 1000:
        log(f"Missing local documents report already generated at {report_file_1}. Checking DB...")

    cur = conn.cursor()
    cur.execute("""
        SELECT DocumentID, ProjectName, DocumentName, DocumentURI, Desc, Notes, Category, AddedOn
        FROM documents
    """)
    rows = cur.fetchall()

    missing_docs = []
    for doc_id, proj, name, uri, desc, notes, cat, added_on in rows:
        if not uri or not uri.strip():
            continue  # Direct text notes / memos without files are preserved

        u = uri.strip()
        ulow = u.lower()
        if ulow.startswith("http://") or ulow.startswith("https://") or ulow.startswith("www."):
            continue  # URL, handled separately

        # Local file resolution
        resolved = None
        if os.path.isabs(u):
            if os.path.exists(u):
                resolved = u
            else:
                alt = os.path.join(DOC_FOLDER, os.path.splitdrive(u)[1].lstrip(r"\/"))
                if os.path.exists(alt):
                    resolved = alt
        else:
            cand = os.path.join(DOC_FOLDER, u.lstrip(r"\/"))
            if os.path.exists(cand):
                resolved = cand

        if not resolved:
            missing_docs.append({
                "DocumentID": doc_id,
                "ProjectName": proj or "",
                "DocumentName": name or "",
                "DocumentURI": uri or "",
                "ResolvedPath": cand if not os.path.isabs(u) else u,
                "Desc": desc or "",
                "Notes": notes or "",
                "Category": cat or "",
                "AddedOn": added_on or "",
            })

    if not missing_docs:
        log("No remaining missing local documents found in database. (Already cleaned up).")
        return []

    log(f"Found {len(missing_docs):,} missing local document entries in database.")

    # Export to CSV
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_file_2 = os.path.join(DOC_FOLDER, "missing_local_documents.csv")

    fieldnames = ["DocumentID", "ProjectName", "DocumentName", "DocumentURI", "ResolvedPath", "Desc", "Notes", "Category", "AddedOn"]
    for out_path in [report_file_1, report_file_2]:
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(missing_docs)
        log(f"Saved missing local documents report: {out_path}")

    # Delete missing documents from DB
    deleted_ids = [d["DocumentID"] for d in missing_docs]
    if deleted_ids:
        log(f"Deleting {len(deleted_ids):,} missing document records from database...")
        batch_size = 500
        for i in range(0, len(deleted_ids), batch_size):
            batch = deleted_ids[i:i + batch_size]
            placeholders = ",".join("?" for _ in batch)
            cur.execute(f"DELETE FROM documents WHERE DocumentID IN ({placeholders})", batch)
            cur.execute(f"DELETE FROM TrackTempFileToDocConv WHERE DocumentID IN ({placeholders})", batch)
            cur.execute(f"DELETE FROM document_chunks WHERE file_id IN ({placeholders})", batch)
        conn.commit()
        log(f"Successfully deleted {len(deleted_ids):,} missing document records.")

    return deleted_ids


def check_google_url(row):
    doc_id, proj, name, uri, desc, notes, cat, added_on = row
    u = uri.strip()

    try:
        r = requests.get(u, headers=HEADERS, stream=True, timeout=5, allow_redirects=True)
        status_code = r.status_code
        r.close()

        if status_code in (404, 410, 400):
            return {
                "inaccessible": True,
                "DocumentID": doc_id,
                "ProjectName": proj or "",
                "DocumentName": name or "",
                "DocumentURI": u,
                "HTTPStatusCode": status_code,
                "ErrorReason": f"HTTP {status_code}",
                "Desc": desc or "",
                "Notes": notes or "",
                "Category": cat or "",
                "AddedOn": added_on or "",
            }
        else:
            return {"inaccessible": False, "status_code": status_code}
    except Exception as e:
        # Retry once briefly
        try:
            r = requests.get(u, headers=HEADERS, stream=True, timeout=6, allow_redirects=True)
            status_code = r.status_code
            r.close()
            if status_code in (404, 410, 400):
                return {
                    "inaccessible": True,
                    "DocumentID": doc_id,
                    "ProjectName": proj or "",
                    "DocumentName": name or "",
                    "DocumentURI": u,
                    "HTTPStatusCode": status_code,
                    "ErrorReason": f"HTTP {status_code}",
                    "Desc": desc or "",
                    "Notes": notes or "",
                    "Category": cat or "",
                    "AddedOn": added_on or "",
                }
            return {"inaccessible": False, "status_code": status_code}
        except Exception as retry_err:
            err_msg = str(retry_err)
            if len(err_msg) > 60:
                err_msg = err_msg[:60] + "..."
            return {
                "inaccessible": True,
                "DocumentID": doc_id,
                "ProjectName": proj or "",
                "DocumentName": name or "",
                "DocumentURI": u,
                "HTTPStatusCode": 0,
                "ErrorReason": f"Connection Error: {err_msg}",
                "Desc": desc or "",
                "Notes": notes or "",
                "Category": cat or "",
                "AddedOn": added_on or "",
            }


def step4_unaccessible_google_docs(conn: sqlite3.Connection) -> list[int]:
    log("=== STEP 4: Scanning Google Drive / Docs URLs for Accessibility ===")
    cur = conn.cursor()
    cur.execute("""
        SELECT DocumentID, ProjectName, DocumentName, DocumentURI, Desc, Notes, Category, AddedOn
        FROM documents
        WHERE DocumentURI LIKE '%google.com%' OR DocumentURI LIKE '%drive.google%'
    """)
    rows = cur.fetchall()
    log(f"Total Google Drive / Docs URLs to test: {len(rows):,}")

    inaccessible_list = []
    status_counts = {}
    completed = 0
    total = len(rows)

    with ThreadPoolExecutor(max_workers=60) as executor:
        futures = {executor.submit(check_google_url, row): row for row in rows}
        for f in as_completed(futures):
            res = f.result()
            completed += 1
            if res["inaccessible"]:
                inaccessible_list.append(res)
                code = res.get("HTTPStatusCode", 0)
                status_counts[code] = status_counts.get(code, 0) + 1
            else:
                code = res.get("status_code", 200)
                status_counts[code] = status_counts.get(code, 0) + 1

            if completed % 500 == 0 or completed == total:
                log(f"Progress: {completed:,}/{total:,} URLs checked. Inaccessible found: {len(inaccessible_list):,}")

    log(f"URL scan complete. Breakdown: {status_counts}")
    log(f"Total inaccessible/dead Google URLs identified: {len(inaccessible_list):,}")

    # Export to CSV
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_file_1 = os.path.join(REPORTS_DIR, "unaccessible_google_docs.csv")
    report_file_2 = os.path.join(DOC_FOLDER, "unaccessible_google_docs.csv")

    fieldnames = [
        "DocumentID", "ProjectName", "DocumentName", "DocumentURI",
        "HTTPStatusCode", "ErrorReason", "Desc", "Notes", "Category", "AddedOn"
    ]
    cleaned_rows = []
    for item in inaccessible_list:
        cleaned_rows.append({k: item[k] for k in fieldnames})

    for out_path in [report_file_1, report_file_2]:
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cleaned_rows)
        log(f"Saved unaccessible Google Docs report: {out_path}")

    # Delete from DB
    deleted_ids = [d["DocumentID"] for d in inaccessible_list]
    if deleted_ids:
        log(f"Deleting {len(deleted_ids):,} inaccessible Google document records from database...")
        batch_size = 500
        for i in range(0, len(deleted_ids), batch_size):
            batch = deleted_ids[i:i + batch_size]
            placeholders = ",".join("?" for _ in batch)
            cur.execute(f"DELETE FROM documents WHERE DocumentID IN ({placeholders})", batch)
            cur.execute(f"DELETE FROM TrackTempFileToDocConv WHERE DocumentID IN ({placeholders})", batch)
            cur.execute(f"DELETE FROM document_chunks WHERE file_id IN ({placeholders})", batch)
        conn.commit()
        log(f"Successfully deleted {len(deleted_ids):,} inaccessible Google document records.")

    return deleted_ids


def step5_clean_old_embeddings(conn: sqlite3.Connection):
    log("=== STEP 5: Removing Old Embeddings and Resetting Status ===")
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM Embeddings")
    c1 = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM Embeddings_backup")
    c2 = cur.fetchone()[0]
    log(f"Current Embeddings rows: {c1:,}, Embeddings_backup rows: {c2:,}")

    cur.execute("DELETE FROM Embeddings")
    cur.execute("DELETE FROM Embeddings_backup")
    log("Cleared all rows from Embeddings and Embeddings_backup.")

    # Reset EmbeddingStatus on remaining documents to 'PENDING'
    cur.execute("""
        UPDATE documents
        SET EmbeddingStatus = 'PENDING', EmbeddingError = NULL
    """)
    updated_count = cur.rowcount
    conn.commit()
    log(f"Reset EmbeddingStatus to 'PENDING' for {updated_count:,} valid documents.")


def step6_delete_text_fragments():
    log("=== STEP 6: Deleting Legacy Text Fragments and UrlsEmbeddings ===")
    deleted_full_txt = 0
    deleted_vect = 0

    for root, dirs, files in os.walk(DOC_FOLDER):
        if "UrlsEmbeddings" in root:
            continue
        for f in files:
            if f.endswith("_full.txt"):
                p = os.path.join(root, f)
                try:
                    os.remove(p)
                    deleted_full_txt += 1
                except Exception as e:
                    log(f"Warning: Could not remove {p}: {e}")
            elif f.endswith(".vect"):
                p = os.path.join(root, f)
                try:
                    os.remove(p)
                    deleted_vect += 1
                except Exception as e:
                    log(f"Warning: Could not remove {p}: {e}")

    log(f"Deleted {deleted_full_txt:,} *_full.txt files and {deleted_vect:,} *.vect files from DocFolder.")

    # Remove UrlsEmbeddings folder
    urls_emb_dir = os.path.join(DOC_FOLDER, "UrlsEmbeddings")
    if os.path.exists(urls_emb_dir):
        count_in_urls = len(os.listdir(urls_emb_dir))
        try:
            shutil.rmtree(urls_emb_dir)
            log(f"Removed UrlsEmbeddings directory ({count_in_urls:,} files).")
        except Exception as e:
            log(f"Warning: Could not remove {urls_emb_dir}: {e}")


def step7_vacuum_and_sync(conn: sqlite3.Connection):
    log("=== STEP 7: Optimizing and Vacuuming Database ===")
    conn.close()

    # Open fresh connection for VACUUM
    v_conn = sqlite3.connect(DB_PATH)
    cur = v_conn.cursor()
    size_before = os.path.getsize(DB_PATH)
    log(f"Database size before VACUUM: {size_before:,} bytes ({size_before / (1024*1024):.2f} MB)")

    log("Executing VACUUM...")
    cur.execute("VACUUM")
    log("Executing PRAGMA optimize...")
    cur.execute("PRAGMA optimize")
    v_conn.close()

    size_after = os.path.getsize(DB_PATH)
    savings = size_before - size_after
    log(f"Database size after VACUUM: {size_after:,} bytes ({size_after / (1024*1024):.2f} MB)")
    log(f"Reclaimed disk space: {savings:,} bytes ({savings / (1024*1024):.2f} MB)")

    # Sync to LocalAppData if it exists
    if os.path.exists(LOCAL_APP_DB):
        try:
            shutil.copy2(DB_PATH, LOCAL_APP_DB)
            log(f"Synchronized cleaned database to LocalAppData: {LOCAL_APP_DB}")
        except Exception as e:
            log(f"Warning: could not sync to LocalAppData: {e}")


def main():
    log("Starting DigitalBrainEX Database & Storage Cleanup...")
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Step 1: Backup DB
    step1_backup_database(timestamp_str)

    # Step 2: Backup Text Fragments
    step2_backup_text_fragments(timestamp_str)

    # Connect to DB for modifications
    conn = sqlite3.connect(DB_PATH)
    try:
        # Step 3: Missing local documents
        missing_ids = step3_missing_local_documents(conn)

        # Step 4: Unaccessible Google docs
        inaccessible_ids = step4_unaccessible_google_docs(conn)

        # Step 5: Clean old embeddings & reset status
        step5_clean_old_embeddings(conn)
    finally:
        conn.close()

    # Step 6: Delete text fragments on disk
    step6_delete_text_fragments()

    # Step 7: Vacuum and sync
    conn = sqlite3.connect(DB_PATH)
    step7_vacuum_and_sync(conn)

    log("=== CLEANUP SUMMARY ===")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM documents")
    final_docs = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM Embeddings")
    final_emb = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM Embeddings_backup")
    final_emb_bak = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM document_chunks")
    final_chunks = cur.fetchone()[0]
    conn.close()

    log(f"Remaining valid documents: {final_docs:,}")
    log(f"Embeddings rows: {final_emb}")
    log(f"Embeddings_backup rows: {final_emb_bak}")
    log(f"document_chunks rows: {final_chunks}")
    log("Database and Storage Cleanup Completed Successfully!")


if __name__ == "__main__":
    main()
