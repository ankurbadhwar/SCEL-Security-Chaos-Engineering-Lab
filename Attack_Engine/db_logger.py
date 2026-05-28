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


# ─── Orchestration Runs ─────────────────────────────────────────────────────

def _init_runs_table():
    """Create the orchestration_runs table if it does not exist."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orchestration_runs (
            run_id          TEXT    PRIMARY KEY,
            start_time      TEXT    NOT NULL,
            end_time        TEXT,
            phase           TEXT    NOT NULL,
            status          TEXT    NOT NULL,
            attacks         TEXT,
            config          TEXT,
            error           TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_run_start(run_id: str, phase: str, attacks: list, config: dict = None):
    """Record the start of an orchestration run."""
    _init_runs_table()
    import json as _json
    conn = _get_connection()
    conn.execute("""
        INSERT INTO orchestration_runs
            (run_id, start_time, phase, status, attacks, config)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        datetime.now().isoformat(),
        phase,
        "running",
        _json.dumps(attacks),
        _json.dumps(config) if config else None,
    ))
    conn.commit()
    conn.close()


def log_run_end(run_id: str, status: str, error: str = None):
    """Record the completion of an orchestration run."""
    _init_runs_table()
    conn = _get_connection()
    conn.execute("""
        UPDATE orchestration_runs
        SET end_time = ?, status = ?, error = ?
        WHERE run_id = ?
    """, (
        datetime.now().isoformat(),
        status,
        error,
        run_id,
    ))
    conn.commit()
    conn.close()


def get_run_history(limit: int = 50):
    """Return recent orchestration runs as a list of dicts."""
    _init_runs_table()
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM orchestration_runs ORDER BY start_time DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_results_by_run(run_id: str):
    """Return attack results that were logged during a specific run."""
    init_db()
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM attack_results WHERE details LIKE ? OR id IN "
        "(SELECT id FROM attack_results ORDER BY id DESC LIMIT 20)",
        (f"%{run_id}%",)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
