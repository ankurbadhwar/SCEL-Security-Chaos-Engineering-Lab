"""
Engine API Server
==================
Thin Flask HTTP layer over the Attack Orchestrator.

Provides endpoints for the Metrics Dashboard to:
  - Start/stop attack runs
  - Poll orchestration status
  - Toggle security controls on the target
  - Retrieve persisted results

Port: 5002 (configurable via config.ENGINE_API_PORT)
Auth: X-API-Key header on mutation endpoints

Usage:
    cd Attack_Engine/
    python engine_api.py
"""

import sys
import os
import uuid
import threading
import time
from functools import wraps
from datetime import datetime

# Ensure imports work from Attack_Engine directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify

from config import ENGINE_API_KEY, ENGINE_API_PORT, TARGET_URL
from orchestrator import AttackOrchestrator, ALL_CHAOS_CONTROLS
from dashboard_reporter import toggle_control
from db_logger import (
    get_all_results, clear_results,
    log_run_start, log_run_end, get_run_history,
)
from brute_force_attack import run_brute_force
from idor_attack import run_idor_attack
from command_injection_attack import run_command_injection
from file_upload_attack import run_file_upload
from csrf_attack import run_csrf_attack

app = Flask(__name__)


# ─── Terminal Logger ─────────────────────────────────────────────────────────

def _log(msg: str, symbol: str = "  "):
    """Print a timestamped line to the Engine API terminal."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {symbol} {msg}", flush=True)

# ─── Attack Registry (mirrors run_demo.py) ──────────────────────────────────

ATTACK_REGISTRY = {
    "brute_force": {
        "fn": run_brute_force,
        "attack_type": "Brute Force Login",
        "chaos_controls": ["RATE_LIMIT_ENABLED", "INPUT_SANITIZATION_ENABLED"],
    },
    "idor": {
        "fn": run_idor_attack,
        "attack_type": "IDOR Access",
        "chaos_controls": ["RBAC_ENABLED", "IDOR_PROTECTION"],
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

# ─── Orchestration State (thread-safe) ──────────────────────────────────────

_state_lock = threading.Lock()
_orchestration_state = {
    "status": "idle",        # idle | running | stopping | completed | failed
    "run_id": None,
    "phase": None,           # before | after | both
    "current_phase": None,   # before_chaos | after_chaos
    "progress": 0,           # 0-100
    "total_attacks": 0,
    "completed_attacks": 0,
    "current_attack": None,
    "start_time": None,
    "results": [],
    "error": None,
}

_execution_thread = None
_stop_event = threading.Event()

# Rate limit for /api/execute
_last_execute_time = 0
_EXECUTE_COOLDOWN = 10  # seconds


def _get_state():
    """Thread-safe read of orchestration state."""
    with _state_lock:
        return dict(_orchestration_state)


def _set_state(**kwargs):
    """Thread-safe update of orchestration state."""
    with _state_lock:
        _orchestration_state.update(kwargs)


# ─── Auth Decorator ─────────────────────────────────────────────────────────

def require_api_key(f):
    """Validate X-API-Key header on mutation endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key", "")
        if key != ENGINE_API_KEY:
            return jsonify({"error": "Unauthorized", "message": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated


# ─── Execution Thread ───────────────────────────────────────────────────────

def _run_orchestration(run_id: str, phase: str, attacks: list, send_dashboard: bool):
    """Execute attacks in a background thread."""
    try:
        # Build filtered registry
        if attacks:
            registry = {k: v for k, v in ATTACK_REGISTRY.items() if k in attacks}
        else:
            registry = dict(ATTACK_REGISTRY)

        if not registry:
            _set_state(status="failed", error="No valid attacks selected")
            log_run_end(run_id, "failed", "No valid attacks selected")
            _log(f"Run {run_id} FAILED — no valid attacks selected", "❌")
            return

        total = len(registry)
        if phase == "both":
            total *= 2

        _set_state(total_attacks=total, completed_attacks=0, progress=0)

        orch = AttackOrchestrator(registry, enabled_controls=6, total_controls=6)
        all_results = []

        # ── Before chaos phase ──────────────────────────────────────────
        if phase in ("before", "both"):
            if _stop_event.is_set():
                _set_state(status="idle", current_phase=None)
                log_run_end(run_id, "stopped")
                return

            _log(f"[{run_id}] Phase: BEFORE CHAOS", "▶️")
            _set_state(current_phase="before_chaos")
            before_results = orch.run_before_chaos(send_dashboard)

            for i, r in enumerate(before_results):
                completed = len(all_results) + i + 1
                attack = r.get('attack_type', 'unknown')
                outcome = '✅ Mitigated' if not r.get('success') else '❌ Bypassed'
                tte = r.get('tte', 0)
                _log(f"  [{run_id}] {attack:30s} {outcome}  TTE={tte:.2f}s", "  ")
                _set_state(
                    completed_attacks=completed,
                    current_attack=attack,
                    progress=int((completed / total) * 100),
                    results=all_results + before_results[:i+1],
                )
                if _stop_event.is_set():
                    _set_state(status="idle", current_phase=None)
                    log_run_end(run_id, "stopped")
                    _log(f"[{run_id}] STOPPED during before_chaos", "🛑")
                    return

            all_results.extend(before_results)

        # ── After chaos phase ───────────────────────────────────────────
        if phase in ("after", "both"):
            if _stop_event.is_set():
                _set_state(status="idle", current_phase=None)
                log_run_end(run_id, "stopped")
                return

            _log(f"[{run_id}] Phase: AFTER CHAOS", "▶️")
            _set_state(current_phase="after_chaos")
            after_results = orch.run_after_chaos(send_dashboard)

            for i, r in enumerate(after_results):
                completed = len(all_results) + i + 1
                attack = r.get('attack_type', 'unknown')
                outcome = '✅ Mitigated' if not r.get('success') else '❌ Bypassed'
                tte = r.get('tte', 0)
                _log(f"  [{run_id}] {attack:30s} {outcome}  TTE={tte:.2f}s", "  ")
                _set_state(
                    completed_attacks=completed,
                    current_attack=attack,
                    progress=int((completed / total) * 100),
                    results=all_results + after_results[:i+1],
                )
                if _stop_event.is_set():
                    _set_state(status="idle", current_phase=None)
                    log_run_end(run_id, "stopped")
                    return

            all_results.extend(after_results)

        _set_state(
            status="completed",
            progress=100,
            results=all_results,
            current_attack=None,
            current_phase=None,
        )
        log_run_end(run_id, "completed")
        _log(f"Run {run_id} COMPLETED  ({len(all_results)} results)", "✅")

    except Exception as exc:
        _set_state(status="failed", error=str(exc), current_phase=None)
        log_run_end(run_id, "failed", str(exc))
        _log(f"Run {run_id} FAILED: {exc}", "❌")


# ─── API Routes ─────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Heartbeat endpoint."""
    return jsonify({
        "service": "scel-engine-api",
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "orchestrator_status": _get_state()["status"],
    })


@app.route("/api/status", methods=["GET"])
def status():
    """Return current orchestration state."""
    state = _get_state()
    return jsonify(state)


@app.route("/api/execute", methods=["POST"])
@require_api_key
def execute():
    """Start an attack run.

    JSON body:
        phase:    "before" | "after" | "both" (default: "both")
        attacks:  ["brute_force", "idor", ...] or [] for all (default: all)
        send_dashboard: true/false (default: true)
    """
    global _execution_thread, _last_execute_time

    # Rate limit
    now = time.time()
    if now - _last_execute_time < _EXECUTE_COOLDOWN:
        remaining = int(_EXECUTE_COOLDOWN - (now - _last_execute_time))
        return jsonify({
            "error": "Rate limited",
            "message": f"Wait {remaining}s before starting another run",
        }), 429

    # Check not already running
    current = _get_state()
    if current["status"] == "running":
        return jsonify({
            "error": "Conflict",
            "message": "An orchestration run is already in progress",
            "run_id": current["run_id"],
        }), 409

    data = request.get_json(silent=True) or {}
    phase = data.get("phase", "both")
    attacks = data.get("attacks", [])
    send_dashboard = data.get("send_dashboard", True)

    # Validate phase
    if phase not in ("before", "after", "both"):
        return jsonify({"error": "Invalid phase. Must be: before, after, both"}), 400

    # Validate attacks
    if attacks:
        invalid = [a for a in attacks if a not in ATTACK_REGISTRY]
        if invalid:
            return jsonify({
                "error": f"Invalid attacks: {invalid}",
                "valid_attacks": list(ATTACK_REGISTRY.keys()),
            }), 400

    run_id = str(uuid.uuid4())[:8]
    _stop_event.clear()
    _last_execute_time = now

    _set_state(
        status="running",
        run_id=run_id,
        phase=phase,
        current_phase=None,
        progress=0,
        total_attacks=0,
        completed_attacks=0,
        current_attack=None,
        start_time=datetime.now().isoformat(),
        results=[],
        error=None,
    )

    log_run_start(run_id, phase, attacks or list(ATTACK_REGISTRY.keys()))

    # Clear the metrics dashboard for a clean slate on each new run
    if send_dashboard:
        try:
            import requests as _req
            from config import DASHBOARD_URL as _DASH_URL
            _req.post(f"{_DASH_URL}/api/experiments/clear", timeout=3)
            _log(f"Metrics dashboard cleared for fresh run", "🧹")
        except Exception:
            pass

    _log(f"Run {run_id} STARTED  phase={phase}  attacks={attacks or list(ATTACK_REGISTRY.keys())}", "🚀")

    _execution_thread = threading.Thread(
        target=_run_orchestration,
        args=(run_id, phase, attacks, send_dashboard),
        daemon=True,
    )
    _execution_thread.start()

    return jsonify({
        "message": "Orchestration started",
        "run_id": run_id,
        "phase": phase,
        "attacks": attacks or list(ATTACK_REGISTRY.keys()),
    }), 202


@app.route("/api/stop", methods=["POST"])
@require_api_key
def stop():
    """Stop a running orchestration."""
    current = _get_state()
    if current["status"] != "running":
        return jsonify({"error": "No run in progress"}), 400

    _stop_event.set()
    _set_state(status="stopping")
    _log(f"Run {current['run_id']} STOPPED by API request", "🛑")
    return jsonify({"message": "Stop signal sent", "run_id": current["run_id"]})


@app.route("/api/controls", methods=["POST"])
@require_api_key
def controls():
    """Toggle security controls on the target webapp."""
    data = request.get_json(silent=True) or {}

    # Batch mode
    if "controls" in data:
        results = {}
        for control, value in data["controls"].items():
            if control not in ALL_CHAOS_CONTROLS:
                results[control] = {"error": f"Invalid control. Valid: {ALL_CHAOS_CONTROLS}"}
                continue
            if not isinstance(value, bool):
                results[control] = {"error": "Value must be boolean"}
                continue
            ok = toggle_control(control, value, verbose=True)
            results[control] = {"success": ok, "value": value}
            if ok:
                _log(f"[BATCH] {control} → {'ON' if value else 'OFF'}", "🔧")
        return jsonify({"results": results})

    # Single mode
    control = data.get("control", "")
    value = data.get("value")

    if control not in ALL_CHAOS_CONTROLS:
        return jsonify({
            "error": f"Invalid control: {control}",
            "valid_controls": ALL_CHAOS_CONTROLS,
        }), 400

    if not isinstance(value, bool):
        return jsonify({"error": "Value must be boolean"}), 400

    ok = toggle_control(control, value, verbose=True)
    if ok:
        _log(f"{control} → {'ON  ✅' if value else 'OFF ❌'}  (via API)", "🔧")
    return jsonify({"success": ok, "control": control, "value": value})


@app.route("/api/results", methods=["GET"])
def results():
    """Return all persisted attack results."""
    limit = request.args.get("limit", 100, type=int)
    all_res = get_all_results()
    return jsonify(all_res[-limit:])


@app.route("/api/results/clear", methods=["POST"])
@require_api_key
def results_clear():
    """Clear all persisted results."""
    clear_results()
    return jsonify({"message": "Results cleared"})


@app.route("/api/history", methods=["GET"])
def history():
    """Return orchestration run history."""
    limit = request.args.get("limit", 50, type=int)
    return jsonify(get_run_history(limit))


@app.route("/api/attacks", methods=["GET"])
def list_attacks():
    """Return available attacks and their metadata."""
    attacks = {}
    for name, entry in ATTACK_REGISTRY.items():
        attacks[name] = {
            "attack_type": entry["attack_type"],
            "chaos_controls": entry["chaos_controls"],
        }
    return jsonify(attacks)


@app.route("/api/controls/status", methods=["GET"])
def controls_status():
    """Query current control states from target webapp."""
    import requests as req_lib
    try:
        resp = req_lib.get(f"{TARGET_URL}/status", timeout=3)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify({"error": "Cannot reach target webapp"}), 503


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n  🚀 SCEL Engine API starting on port {ENGINE_API_PORT}")
    print(f"  📡 Target webapp: {TARGET_URL}")
    print(f"  🔑 API key required for mutation endpoints\n")
    app.run(host="0.0.0.0", port=ENGINE_API_PORT, debug=False)
