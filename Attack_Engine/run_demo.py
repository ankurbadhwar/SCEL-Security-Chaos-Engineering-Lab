#!/usr/bin/env python3
"""
SCEL Attack Simulation Engine — Full Demo Orchestrator
========================================================

This is the MAIN script that demonstrates the core SCEL loop:

    1. Security controls ON  → run attacks → observe failure / high TTE
    2. Disable controls (chaos injection)
    3. Run attacks again     → observe success / low TTE
    4. Compare resilience scores

Usage:
    cd Attack_Engine/
    python run_demo.py                  # full demo (both phases)
    python run_demo.py --phase before   # only "before chaos"
    python run_demo.py --phase after    # only "after chaos"
    python run_demo.py --no-dashboard   # skip sending to dashboard
    python run_demo.py --clear-db       # wipe previous results first

Requires:
    - Target webapp running on http://127.0.0.1:5000  (cd Target_webapp && python -m app.app)
    - (Optional) Metrics dashboard on http://192.168.1.5:5000
"""

import sys
import os
import json
import argparse
import time
import requests as req_lib

# Ensure imports work when run from the Attack_Engine directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brute_force_attack import run_brute_force
from idor_attack import run_idor_attack
from command_injection_attack import run_command_injection
from file_upload_attack import run_file_upload
from csrf_attack import run_csrf_attack
from db_logger import log_attack, get_all_results, clear_results
from dashboard_reporter import send_to_dashboard, toggle_control
from config import TARGET_URL
from orchestrator import AttackOrchestrator


def reset_rate_limit():
    """Clear server-side rate-limit counters."""
    try:
        req_lib.post(f"{TARGET_URL}/reset-rate-limit", timeout=3)
    except Exception:
        pass


# ─── Resilience score (local copy, matches Metrics/scoring.py) ───────────────
def calculate_resilience(enabled: int, total: int, tte: float, success: bool) -> float:
    defense = enabled / total if total > 0 else 0
    tte_norm = min(tte / 10.0, 1.0)
    success_val = 1 if success else 0
    return round((defense * tte_norm) / (success_val + 1) * 100, 2)


# ─── Attack registry ─────────────────────────────────────────────────────────
# Each entry: fn = callable returning the standard result dict.
# chaos_controls lists which target controls this attack probes.
ATTACK_REGISTRY = {
    "brute_force": {
        "fn": run_brute_force,
        "attack_type": "Brute Force Login",
        "chaos_controls": ["RATE_LIMIT_ENABLED", "INPUT_SANITIZATION_ENABLED"],
    },
    "idor": {
        "fn": run_idor_attack,
        "attack_type": "IDOR Access",
        "chaos_controls": ["RBAC_ENABLED"],
    },
    "command_injection": {
        "fn": run_command_injection,
        "attack_type": "Command Injection",
        "chaos_controls": ["INPUT_SANITIZATION_ENABLED"],
    },
    "file_upload": {
        "fn": run_file_upload,
        "attack_type": "Unrestricted File Upload",
        "chaos_controls": ["INPUT_SANITIZATION_ENABLED"],
    },
    "csrf": {
        "fn": run_csrf_attack,
        "attack_type": "CSRF Transfer",
        "chaos_controls": ["CSRF_PROTECTION"],
    },
}


# ─── Helpers ─────────────────────────────────────────────────────────────────
BANNER = r"""
 ╔═══════════════════════════════════════════════════════════════╗
 ║   ███████╗ ██████╗███████╗██╗                                ║
 ║   ██╔════╝██╔════╝██╔════╝██║                                ║
 ║   ███████╗██║     █████╗  ██║                                ║
 ║   ╚════██║██║     ██╔══╝  ██║                                ║
 ║   ███████║╚██████╗███████╗███████╗                           ║
 ║   ╚══════╝ ╚═════╝╚══════╝╚══════╝                           ║
 ║                                                               ║
 ║   Security Chaos Engineering Lab — Attack Simulation Engine   ║
 ╚═══════════════════════════════════════════════════════════════╝
"""

PHASE_HEADER = """
 ┌──────────────────────────────────────────────────────────┐
 │  PHASE: {phase:<49}│
 │  Controls: {controls:<47}│
 └──────────────────────────────────────────────────────────┘
"""


def print_summary_table(results: list[dict]):
    """Pretty-print a summary table of attack results."""
    print(f"\n {'Phase':<16} {'Attack':<22} {'Success':<9} {'TTE (s)':<10} {'Resilience':<12}")
    print(f" {'─'*16} {'─'*22} {'─'*9} {'─'*10} {'─'*12}")
    for r in results:
        phase = r.get("phase", "?")
        attack = r.get("attack_type", r.get("attack", "?"))
        success = "✅ YES" if r.get("success") else "❌ NO"
        tte = f"{r.get('tte', 0):.4f}"
        score = r.get("resilience_score", "—")
        if isinstance(score, (int, float)):
            score = f"{score:.2f}"
        print(f" {phase:<16} {attack:<22} {success:<9} {tte:<10} {score:<12}")
    print()


# ─── Phase runners (delegated to AttackOrchestrator) ─────────────────────────

def _make_orchestrator() -> AttackOrchestrator:
    return AttackOrchestrator(ATTACK_REGISTRY, enabled_controls=3, total_controls=3)


def run_phase_before_chaos(send_dashboard: bool = True) -> list[dict]:
    """Phase 1: All controls ON. Attacks should fail / take long."""
    print(PHASE_HEADER.format(
        phase="BEFORE CHAOS (all controls ON)",
        controls="RATE_LIMIT ✅ | RBAC ✅ | INPUT_SANITIZATION ✅ | CSRF ✅",
    ))
    return _make_orchestrator().run_before_chaos(send_dashboard)


def run_phase_after_chaos(send_dashboard: bool = True) -> list[dict]:
    """Phase 2: All controls OFF. Attacks should succeed quickly."""
    print(PHASE_HEADER.format(
        phase="AFTER CHAOS (all controls OFF)",
        controls="RATE_LIMIT ❌ | RBAC ❌ | INPUT_SANITIZATION ❌ | CSRF ❌",
    ))
    return _make_orchestrator().run_after_chaos(send_dashboard)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SCEL Attack Simulation Engine — Full Demo"
    )
    parser.add_argument(
        "--phase", choices=["before", "after", "both"], default="both",
        help="Which phase to run (default: both)"
    )
    parser.add_argument(
        "--no-dashboard", action="store_true",
        help="Skip sending results to the metrics dashboard"
    )
    parser.add_argument(
        "--clear-db", action="store_true",
        help="Clear previous attack results from the database before running"
    )
    args = parser.parse_args()

    print(BANNER)

    send_dashboard = not args.no_dashboard

    if args.clear_db:
        clear_results()
        print("  🗑️  Previous results cleared.\n")

    all_results = []

    if args.phase in ("before", "both"):
        all_results.extend(run_phase_before_chaos(send_dashboard))

    if args.phase == "both":
        print("\n" + "═" * 60)
        print("  ⚡ TRANSITIONING TO CHAOS PHASE...")
        print("═" * 60)
        time.sleep(1)

    if args.phase in ("after", "both"):
        all_results.extend(run_phase_after_chaos(send_dashboard))


    # ── Final Summary ────────────────────────────────────────────────────
    print("\n" + "═" * 70)
    print("  📊 ATTACK SIMULATION SUMMARY")
    print("═" * 70)
    print_summary_table(all_results)

    # Show degradation analysis if both phases ran
    if args.phase == "both" and len(all_results) >= 4:
        before = [r for r in all_results if r["phase"] == "before_chaos"]
        after  = [r for r in all_results if r["phase"] == "after_chaos"]

        before_scores = [r["resilience_score"] for r in before]
        after_scores  = [r["resilience_score"] for r in after]

        avg_before = sum(before_scores) / len(before_scores) if before_scores else 0
        avg_after  = sum(after_scores) / len(after_scores) if after_scores else 0

        print(f"  📈 Avg Resilience (Before Chaos): {avg_before:.2f}")
        print(f"  📉 Avg Resilience (After Chaos) : {avg_after:.2f}")

        if avg_before > 0:
            drop = ((avg_before - avg_after) / avg_before) * 100
            print(f"  ⬇️  Resilience Drop: {drop:.1f}%")
        print()
        print("  ╔═══════════════════════════════════════════════════════╗")
        print("  ║  CONCLUSION: Security failure leads to faster        ║")
        print("  ║  compromise and lower system resilience.             ║")
        print("  ╚═══════════════════════════════════════════════════════╝")
        print()

    # ── Also dump all stored results ─────────────────────────────────────
    all_stored = get_all_results()
    if all_stored:
        print(f"  💾 {len(all_stored)} results stored in SQLite database.")
        print(f"     Database: Attack_Engine/attack_results.db\n")

    # ── Save JSON summary ────────────────────────────────────────────────
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_summary.json")
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  📄 Results also saved to: {json_path}\n")


if __name__ == "__main__":
    main()
