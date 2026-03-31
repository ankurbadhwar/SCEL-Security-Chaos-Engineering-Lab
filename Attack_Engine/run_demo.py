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
from db_logger import log_attack, get_all_results, clear_results
from dashboard_reporter import send_to_dashboard, toggle_control
from config import TARGET_URL


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


# ─── Phase runners ───────────────────────────────────────────────────────────

def run_phase_before_chaos(send_dashboard: bool = True):
    """
    Phase 1: All security controls ON. Attacks should fail or take a long time.
    """
    phase = "before_chaos"
    enabled = 3
    total = 3

    print(PHASE_HEADER.format(
        phase="BEFORE CHAOS (all controls ON)",
        controls="RATE_LIMIT ✅ | RBAC ✅ | INPUT_SANITIZATION ✅",
    ))

    # Ensure controls are ON
    toggle_control("RATE_LIMIT_ENABLED", True)
    toggle_control("RBAC_ENABLED", True)
    toggle_control("INPUT_SANITIZATION_ENABLED", True)
    time.sleep(0.5)
    reset_rate_limit()

    results = []

    # ── Attack 1: Brute Force ────────────────────────────────────────────
    bf_result = run_brute_force()
    bf_result["phase"] = phase
    bf_result["enabled_controls"] = enabled
    bf_result["total_controls"] = total
    bf_result["resilience_score"] = calculate_resilience(
        enabled, total, bf_result["tte"], bf_result["success"]
    )
    log_attack(bf_result)
    if send_dashboard:
        send_to_dashboard(bf_result, phase=phase,
                          enabled_controls=enabled, total_controls=total)
    results.append(bf_result)

    # Reset rate-limit counters for clean IDOR test
    reset_rate_limit()

    # ── Attack 2: IDOR ───────────────────────────────────────────────────
    idor_result = run_idor_attack()
    idor_result["phase"] = phase
    idor_result["enabled_controls"] = enabled
    idor_result["total_controls"] = total
    idor_result["resilience_score"] = calculate_resilience(
        enabled, total, idor_result["tte"], idor_result["success"]
    )
    log_attack(idor_result)
    if send_dashboard:
        send_to_dashboard(idor_result, phase=phase,
                          enabled_controls=enabled, total_controls=total)
    results.append(idor_result)

    return results


def run_phase_after_chaos(send_dashboard: bool = True):
    """
    Phase 2: Disable security controls (chaos injection).
    Same attacks should now succeed faster.
    """
    phase = "after_chaos"
    enabled = 0
    total = 3

    print(PHASE_HEADER.format(
        phase="AFTER CHAOS (all controls OFF)",
        controls="RATE_LIMIT ❌ | RBAC ❌ | INPUT_SANITIZATION ❌",
    ))

    # ── Chaos injection: disable all controls ────────────────────────────
    print("  💥 INJECTING CHAOS — disabling all security controls...")
    toggle_control("RATE_LIMIT_ENABLED", False)
    toggle_control("RBAC_ENABLED", False)
    toggle_control("INPUT_SANITIZATION_ENABLED", False)
    time.sleep(0.5)
    reset_rate_limit()

    results = []

    # ── Attack 1: Brute Force ────────────────────────────────────────────
    bf_result = run_brute_force()
    bf_result["phase"] = phase
    bf_result["enabled_controls"] = enabled
    bf_result["total_controls"] = total
    bf_result["resilience_score"] = calculate_resilience(
        enabled, total, bf_result["tte"], bf_result["success"]
    )
    log_attack(bf_result)
    if send_dashboard:
        send_to_dashboard(bf_result, phase=phase,
                          enabled_controls=enabled, total_controls=total)
    results.append(bf_result)

    # ── Attack 2: IDOR ───────────────────────────────────────────────────
    idor_result = run_idor_attack()
    idor_result["phase"] = phase
    idor_result["enabled_controls"] = enabled
    idor_result["total_controls"] = total
    idor_result["resilience_score"] = calculate_resilience(
        enabled, total, idor_result["tte"], idor_result["success"]
    )
    log_attack(idor_result)
    if send_dashboard:
        send_to_dashboard(idor_result, phase=phase,
                          enabled_controls=enabled, total_controls=total)
    results.append(idor_result)

    # ── Restore controls after test ──────────────────────────────────────
    print("\n  🔄 Restoring all security controls...")
    toggle_control("RATE_LIMIT_ENABLED", True)
    toggle_control("RBAC_ENABLED", True)
    toggle_control("INPUT_SANITIZATION_ENABLED", True)

    return results


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
