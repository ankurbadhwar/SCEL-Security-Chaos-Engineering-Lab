# SCEL Attack Simulation Engine

The **Attack Simulation Engine** simulates controlled security attacks against the Target Webapp and measures how security control degradation affects exploit success rate and time-to-exploit (TTE).

---

## Architecture

```
Attack_Engine/
├── config.py              # Target URLs, wordlist, user credentials
├── brute_force_attack.py  # Brute force login simulation
├── idor_attack.py         # IDOR (Insecure Direct Object Reference) simulation
├── db_logger.py           # SQLite persistence for all attack results
├── dashboard_reporter.py  # Sends results to Metrics Dashboard + toggle helper
├── run_demo.py            # Main orchestrator — runs the full demo loop
├── attack_results.db      # SQLite database (auto-created on first run)
└── results_summary.json   # JSON summary of last run (auto-created)
```

---

## Prerequisites

1. **Target Webapp must be running** on `http://127.0.0.1:5000`:
   ```bash
   cd Target_webapp/
   python -m app.app
   ```

2. **Python packages** (already in `requirements.txt`):
   ```bash
   pip install flask requests
   ```

3. **(Optional)** Metrics Dashboard running on `http://192.168.1.5:5000`

---

## Quick Start — Full Demo

```bash
cd Attack_Engine/
python run_demo.py --no-dashboard --clear-db
```

This will:
1. **Phase 1** — Enable all 3 security controls, run both attacks  
   → Brute force gets rate-limited (FAIL), IDOR gets access denied (FAIL)
2. **Phase 2** — Disable all controls (chaos injection), run both attacks  
   → Brute force finds password (SUCCESS), IDOR accesses other user's data (SUCCESS)
3. Print a comparison table showing **resilience score degradation**

---

## Individual Attacks

### Brute Force Login
```bash
python brute_force_attack.py
```
- Tries passwords from a wordlist against `/login`
- Measures TTE (time to exploit) and number of attempts
- Stops when: password found (success) or rate-limited (failure)

### IDOR Attack
```bash
python idor_attack.py
```
- Logs in as `user1` (id=1)
- Attempts to access `/profile/2` (user2's profile)
- If RBAC is on → 403 (failure). If RBAC is off → 200 (success)

---

## Output Format

Each attack returns a dict:
```json
{
  "attack": "brute_force",
  "attack_type": "Brute Force Login",
  "success": true,
  "tte": 2.4,
  "attempts": 15,
  "details": "Password found: 'password123' after 15 attempts"
}
```

---

## CLI Options

| Flag | Description |
|------|-------------|
| `--phase before` | Only run Phase 1 (controls ON) |
| `--phase after` | Only run Phase 2 (controls OFF) |
| `--phase both` | Run both phases (default) |
| `--no-dashboard` | Don't send results to the Metrics Dashboard |
| `--clear-db` | Wipe previous results from SQLite before running |

---

## Sending Results to the Dashboard

The `dashboard_reporter.py` module sends results to the Metrics Dashboard using:

```python
import requests

attack_results = {
    "phase": "after_chaos",
    "attack_type": "Brute Force Login",
    "enabled_controls": 0,
    "total_controls": 3,
    "tte": 2.1,
    "success": True
}

url = "http://192.168.1.5:5000/api/submit"
response = requests.post(url, json=attack_results)
print("Sent to Dashboard:", response.json())
```

---

## Key Demonstration

> **"Security failure leads to faster compromise and lower system resilience."**

| Phase | Brute Force | IDOR | Avg Resilience |
|-------|------------|------|----------------|
| Before Chaos (controls ON) | ❌ Rate limited | ❌ Access denied | ~50 |
| After Chaos (controls OFF) | ✅ Password found fast | ✅ Data leaked | ~0 |
