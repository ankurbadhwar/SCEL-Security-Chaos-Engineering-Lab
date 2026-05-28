"""
Attack Engine Configuration
============================
Central configuration for the attack simulation engine.
Update TARGET_URL to match where the Target Webapp is running.
Update DASHBOARD_URL to match where the Metrics Dashboard is running.
"""

# ─── Target Webapp ───────────────────────────────────────────────────────────
TARGET_URL = "http://127.0.0.1:5000"

# ─── Metrics Dashboard ───────────────────────────────────────────────────────
DASHBOARD_URL = "http://127.0.0.1:5001"

# ─── Engine API Server ───────────────────────────────────────────────────────
ENGINE_API_PORT = 5002
ENGINE_API_KEY = "scel-engine-key-2024"

# ─── Hardcoded Users (must match Target_webapp/models/users.py) ──────────────
USERS = {
    "user1": {"password": "password123", "id": 1},
    "user2": {"password": "password456", "id": 2},
}

# ─── Brute Force Wordlist ────────────────────────────────────────────────────
# The correct password is deliberately placed in the list so the attack
# eventually succeeds. The position controls how long it takes (TTE).
PASSWORD_LIST = [
    "admin",
    "letmein",
    "123456",
    "dragon",
    "monkey",
    "master",
    "qwerty",
    "abc123",
    "welcome",
    "shadow",
    "football",
    "iloveyou",
    "trustno1",
    "sunshine",
    "password123",   # ← correct password for user1 (position matters for TTE)
]

# ─── SQLite Database ─────────────────────────────────────────────────────────
DB_PATH = "attack_results.db"
