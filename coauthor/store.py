"""SQLite persistence for scan history.

Stores scan results in ~/.coauthor/scans.db for later retrieval.
"""

import json
import os
import sqlite3
from typing import Dict, List, Optional


def _db_path() -> str:
    """Return the path to the scans database, creating the directory if needed."""
    base_dir = os.path.join(os.path.expanduser("~"), ".coauthor")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "scans.db")


def _get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the table if needed."""
    db = _db_path()
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scans ("
        "  id TEXT PRIMARY KEY,"
        "  repo_path TEXT,"
        "  commit_sha TEXT,"
        "  created_at TEXT,"
        "  report_json TEXT"
        ")"
    )
    conn.commit()
    return conn


def save_scan(
    scan_id: str,
    repo_path: str,
    commit_sha: str,
    report: Dict,
) -> None:
    """Save a scan result to the database."""
    conn = _get_connection()
    try:
        report_json = json.dumps(report)
        created_at = report.get("scanned_at", "")
        conn.execute(
            "INSERT OR REPLACE INTO scans (id, repo_path, commit_sha, created_at, report_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (scan_id, repo_path, commit_sha, created_at, report_json),
        )
        conn.commit()
    finally:
        conn.close()


def get_scan(scan_id: str) -> Optional[Dict]:
    """Retrieve a scan by ID. Returns None if not found."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT report_json FROM scans WHERE id = ?",
            (scan_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return json.loads(row[0])
    finally:
        conn.close()


def list_scans(repo: str = "", limit: int = 20) -> List[Dict]:
    """List recent scans, optionally filtered by repo path."""
    conn = _get_connection()
    try:
        if repo:
            cursor = conn.execute(
                "SELECT id, repo_path, commit_sha, created_at "
                "FROM scans WHERE repo_path LIKE ? "
                "ORDER BY created_at DESC LIMIT ?",
                ("%" + repo + "%", limit),
            )
        else:
            cursor = conn.execute(
                "SELECT id, repo_path, commit_sha, created_at "
                "FROM scans ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "repo_path": row[1],
                "commit_sha": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]
    finally:
        conn.close()
