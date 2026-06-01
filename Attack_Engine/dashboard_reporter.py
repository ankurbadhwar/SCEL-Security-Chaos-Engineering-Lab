"""
Dashboard Reporter
===================
Sends attack results to Member 1's Metrics Dashboard via the /api/submit endpoint.
Also provides a helper to query the current control states from the target webapp.
"""

import requests
from config import DASHBOARD_URL, TARGET_URL


def get_control_states() -> dict:
    """
    Query the target webapp's /status endpoint to determine which controls
    are currently enabled. Returns counts for the dashboard payload.

    Falls back to defaults if the target is unreachable.
    """
    try:
        resp = requests.get(f"{TARGET_URL}/status", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            total = len(data)
            enabled = sum(1 for v in data.values() if v)
            return {
                "enabled_controls": enabled,
                "total_controls": total,
            }
    except Exception:
        pass

    return {
        "enabled_controls": 6,  # fallback: all 6 controls on
        "total_controls": 6,
    }


def send_to_dashboard(result: dict, phase: str = "before_chaos",
                      enabled_controls: int = 6, total_controls: int = 6,
                      verbose: bool = True) -> dict | None:
    """
    POST an attack result to the Metrics Dashboard.

    Args:
        result:             Attack result dict (from brute_force or idor attack).
        phase:              "before_chaos" or "after_chaos".
        enabled_controls:   Number of security controls currently enabled.
        total_controls:     Total number of security controls.
        verbose:            Print status to stdout.

    Returns:
        Response JSON from the dashboard, or None on failure.
    """
    payload = {
        "phase": phase,
        "attack_type": result.get("attack_type", result.get("attack", "unknown")),
        "enabled_controls": enabled_controls,
        "total_controls": total_controls,
        "tte": result.get("tte", 0.0),
        "success": result.get("success", False),
    }

    url = f"{DASHBOARD_URL}/api/submit"

    if verbose:
        print(f"\n  📡 Sending to dashboard: {url}")
        print(f"     Payload: {payload}")

    try:
        resp = requests.post(url, json=payload, timeout=5)
        data = resp.json()
        if verbose:
            print(f"     Response: {data}")
        return data
    except requests.ConnectionError:
        if verbose:
            print(f"     ⚠️  Dashboard unreachable at {url}")
            print(f"        (This is OK if you're running locally without the dashboard)")
        return None
    except Exception as e:
        if verbose:
            print(f"     ⚠️  Error sending to dashboard: {e}")
        return None


def toggle_control(control: str, value: bool, verbose: bool = True) -> bool:
    """
    Toggle a security control on the target webapp via the /toggle API.

    Args:
        control:  One of RATE_LIMIT_ENABLED, RBAC_ENABLED, INPUT_SANITIZATION_ENABLED
        value:    True to enable, False to disable
        verbose:  Print status

    Returns:
        True if toggle succeeded, False otherwise.
    """
    url = f"{TARGET_URL}/toggle"
    payload = {"control": control, "value": value}

    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            status = "ON ✅" if value else "OFF ❌"
            if verbose:
                print(f"  🔧 {control} → {status}")
            return True
        else:
            if verbose:
                print(f"  ⚠️  Toggle failed: {resp.text}")
            return False
    except requests.ConnectionError:
        if verbose:
            print(f"  ⚠️  Cannot reach target at {url}")
        return False
