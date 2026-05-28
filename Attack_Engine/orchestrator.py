"""
Attack Orchestrator
====================
Registry-driven phase runner for SCEL attack simulations.

Usage:
    from orchestrator import AttackOrchestrator

    registry = {
        "brute_force": {
            "fn": run_brute_force,
            "attack_type": "Brute Force Login",
            "chaos_controls": ["RATE_LIMIT_ENABLED", "INPUT_SANITIZATION_ENABLED"],
        },
        ...
    }

    orch = AttackOrchestrator(registry, enabled_controls=3, total_controls=3)
    results = orch.run(phase="both", send_dashboard=True)

Each attack callable must return a dict matching the db_logger schema:
    attack, attack_type, success, tte[, attempts, details]
"""

import time
import requests as req_lib

from db_logger import log_attack
from dashboard_reporter import send_to_dashboard, toggle_control
from config import TARGET_URL


# Controls toggled during "after chaos" phase (all-OFF) and restored after
ALL_CHAOS_CONTROLS = [
    "RATE_LIMIT_ENABLED",
    "RBAC_ENABLED",
    "INPUT_SANITIZATION_ENABLED",
    "CSRF_PROTECTION",
]


def _reset_rate_limit() -> None:
    """Clear server-side rate-limit counters."""
    try:
        req_lib.post(f"{TARGET_URL}/reset-rate-limit", timeout=3)
    except Exception:
        pass


def _apply_controls(states: dict[str, bool]) -> None:
    """Push a set of control states to the target webapp."""
    for control, value in states.items():
        toggle_control(control, value)
    time.sleep(0.3)


# ─── Resilience scoring (mirrors run_demo.py / Metrics/scoring.py) ──────────

def _calculate_resilience(enabled: int, total: int, tte: float, success: bool) -> float:
    defense = enabled / total if total > 0 else 0
    tte_norm = min(tte / 10.0, 1.0)
    success_val = 1 if success else 0
    return round((defense * tte_norm) / (success_val + 1) * 100, 2)


# ─── Orchestrator ────────────────────────────────────────────────────────────

class AttackOrchestrator:
    """
    Drives attack phases against the SCEL target webapp.

    Args:
        registry:         Dict mapping attack name → {fn, attack_type, chaos_controls}.
        enabled_controls: Number of core controls considered "enabled" in before-chaos phase.
        total_controls:   Denominator for resilience scoring (default 3 for backwards compat).
    """

    def __init__(
        self,
        registry: dict,
        enabled_controls: int = 3,
        total_controls: int = 3,
    ):
        self.registry = registry
        self._enabled_controls = enabled_controls
        self._total_controls = total_controls

    # ── Internal phase runner ────────────────────────────────────────────────

    def _run_phase(
        self,
        phase: str,
        enabled: int,
        send_dashboard: bool,
    ) -> list[dict]:
        results = []
        _reset_rate_limit()

        for name, entry in self.registry.items():
            fn = entry["fn"]

            try:
                result = fn()
            except Exception as exc:
                result = {
                    "attack": name,
                    "attack_type": entry.get("attack_type", name),
                    "success": False,
                    "tte": 0.0,
                    "attempts": None,
                    "details": f"Attack raised exception: {exc}",
                }

            # Annotate with phase context
            result["phase"] = phase
            result["enabled_controls"] = enabled
            result["total_controls"] = self._total_controls
            result["resilience_score"] = _calculate_resilience(
                enabled, self._total_controls, result.get("tte", 0.0), result.get("success", False)
            )

            log_attack(result)

            if send_dashboard:
                send_to_dashboard(
                    result,
                    phase=phase,
                    enabled_controls=enabled,
                    total_controls=self._total_controls,
                )

            results.append(result)
            _reset_rate_limit()  # reset between attacks to avoid state bleed

        return results

    # ── Public API ───────────────────────────────────────────────────────────

    def run_before_chaos(self, send_dashboard: bool = True) -> list[dict]:
        """Phase 1: all controls ON. Attacks should fail / take long."""
        print("\n  🔒 Enabling all security controls...")
        _apply_controls({c: True for c in ALL_CHAOS_CONTROLS})

        return self._run_phase(
            phase="before_chaos",
            enabled=self._enabled_controls,
            send_dashboard=send_dashboard,
        )

    def run_after_chaos(self, send_dashboard: bool = True) -> list[dict]:
        """Phase 2: all controls OFF. Attacks should succeed quickly."""
        print("\n  💥 INJECTING CHAOS — disabling all security controls...")
        _apply_controls({c: False for c in ALL_CHAOS_CONTROLS})

        results = self._run_phase(
            phase="after_chaos",
            enabled=0,
            send_dashboard=send_dashboard,
        )

        print("\n  🔄 Restoring all security controls...")
        _apply_controls({c: True for c in ALL_CHAOS_CONTROLS})

        return results

    def run(self, phase: str = "both", send_dashboard: bool = True) -> list[dict]:
        """
        Run the full demo loop.

        Args:
            phase: "before" | "after" | "both"
            send_dashboard: Forward results to Metrics dashboard.

        Returns:
            List of annotated attack result dicts.
        """
        all_results = []

        if phase in ("before", "both"):
            all_results.extend(self.run_before_chaos(send_dashboard))

        if phase == "both":
            print("\n" + "═" * 60)
            print("  ⚡ TRANSITIONING TO CHAOS PHASE...")
            print("═" * 60)
            time.sleep(1)

        if phase in ("after", "both"):
            all_results.extend(self.run_after_chaos(send_dashboard))

        return all_results
