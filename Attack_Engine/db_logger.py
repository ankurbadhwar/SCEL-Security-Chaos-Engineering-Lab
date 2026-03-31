"""
SQLite Logger for Attack Results
=================================
Creates and manages a local SQLite database to persist every attack result
with full context: phase, controls state, timing, and resilience score.
"""

import sqlite3
import os
from datetime import datetime

# Resolve DB path relative to this file so it works regardless of cwd
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attack_results.db")


def _get_connection():
    """Return a connection to the SQLite database, creating it if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the results table if it does not exist."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attack_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT    NOT NULL,
            phase           TEXT    NOT NULL,
            attack_type     TEXT    NOT NULL,
            success         INTEGER NOT NULL,
            tte             REAL    NOT NULL,
            attempts        INTEGER,
            enabled_controls INTEGER,
            total_controls  INTEGER,
            resilience_score REAL,
            details         TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_attack(result: dict):
    """
    Insert one attack result into the database.

    Expected keys in `result`:
        phase, attack_type, success, tte
    Optional keys:
        attempts, enabled_controls, total_controls, resilience_score, details
    """
    init_db()
    conn = _get_connection()
    conn.execute("""
        INSERT INTO attack_results
            (timestamp, phase, attack_type, success, tte,
             attempts, enabled_controls, total_controls,
             resilience_score, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        result.get("phase", "unknown"),
        result.get("attack_type", result.get("attack", "unknown")),
        1 if result.get("success") else 0,
        result.get("tte", 0.0),
        result.get("attempts"),
        result.get("enabled_controls"),
        result.get("total_controls"),
        result.get("resilience_score"),
        result.get("details"),
    ))
    conn.commit()
    conn.close()


def get_all_results():
    """Return every stored attack result as a list of dicts."""
    init_db()
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM attack_results ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def clear_results():
    """Wipe the results table (useful between demo runs)."""
    init_db()
    conn = _get_connection()
    conn.execute("DELETE FROM attack_results")
    conn.commit()
    conn.close()
