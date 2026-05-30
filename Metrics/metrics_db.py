"""
Metrics Dashboard — SQLite Persistence
========================================
Write-through persistence for dashboard experiments data.
Survives process restarts; loaded on app startup.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metrics.db")


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they do not exist."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT    NOT NULL,
            phase           TEXT    NOT NULL,
            attack_type     TEXT    NOT NULL,
            enabled_controls INTEGER,
            total_controls  INTEGER,
            tte             REAL,
            success         INTEGER,
            score           REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS security_profiles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL UNIQUE,
            controls        TEXT    NOT NULL,
            created_at      TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_experiment(phase: str, data: dict):
    """Persist a single experiment result."""
    init_db()
    conn = _get_connection()
    conn.execute("""
        INSERT INTO experiments
            (timestamp, phase, attack_type, enabled_controls, total_controls, tte, success, score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        phase,
        data.get("attack_type", "unknown"),
        data.get("enabled_controls"),
        data.get("total_controls"),
        data.get("tte", 0.0),
        1 if data.get("success") else 0,
        data.get("score"),
    ))
    conn.commit()
    conn.close()


def load_experiments():
    """Load the most-recent result per (phase, attack_type) from SQLite.
    
    Deliberately returns only the latest entry for each attack in each phase
    so that old runs don’t inflate the live dashboard view.
    """
    init_db()
    conn = _get_connection()
    # Subquery: for each (phase, attack_type) pick the row with the highest id
    rows = conn.execute("""
        SELECT e.* FROM experiments e
        INNER JOIN (
            SELECT phase, attack_type, MAX(id) AS max_id
            FROM experiments
            GROUP BY phase, attack_type
        ) latest ON e.id = latest.max_id
        ORDER BY e.id
    """).fetchall()
    conn.close()

    result = {"before_chaos": [], "after_chaos": []}
    for row in rows:
        entry = dict(row)
        phase = entry.pop("phase", "before_chaos")
        entry["success"] = bool(entry.get("success"))
        if phase in result:
            result[phase].append(entry)
    return result


def clear_experiments():
    """Wipe all experiments."""
    init_db()
    conn = _get_connection()
    conn.execute("DELETE FROM experiments")
    conn.commit()
    conn.close()


def save_profile(name: str, controls: dict):
    """Save a security profile configuration."""
    init_db()
    conn = _get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO security_profiles (name, controls, created_at)
        VALUES (?, ?, ?)
    """, (name, json.dumps(controls), datetime.now().isoformat()))
    conn.commit()
    conn.close()


def load_profiles():
    """Load all saved security profiles."""
    init_db()
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM security_profiles ORDER BY name").fetchall()
    conn.close()
    result = []
    for row in rows:
        entry = dict(row)
        entry["controls"] = json.loads(entry["controls"])
        result.append(entry)
    return result
