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
    "user1": {"password": "user123", "id": 2},
    "user2": {"password": "user456", "id": 3},
}

# ─── Brute Force Wordlist ────────────────────────────────────────────────────
# user2's password is placed near the end so the attack takes multiple attempts.
# Rate limiting (before chaos) triggers before we reach it → attack blocked.
# Without rate limiting (after chaos) all attempts run → password found → exploit succeeds.
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
    "user456",   # ← correct password for user2 (position near end = meaningful TTE)
]

# ─── SQLite Database ─────────────────────────────────────────────────────────
DB_PATH = "attack_results.db"
