from flask import Flask, render_template, request, jsonify, make_response
import requests as req_lib

# Import directly from the local scoring.py file
from scoring import calculate_resilience
from metrics_db import save_experiment, load_experiments, save_profile, load_profiles

app = Flask(__name__)

# ─── Configuration ──────────────────────────────────────────────────────────

ENGINE_API_URL = "http://127.0.0.1:5002"
ENGINE_API_KEY = "scel-engine-key-2024"

# ─── In-memory experiment store (loaded from SQLite on startup) ─────────────

_stored = load_experiments()
experiments = {
    "before_chaos": _stored.get("before_chaos", []),
    "after_chaos": _stored.get("after_chaos", []),
}

# ─── Blast radius mapping ──────────────────────────────────────────────────

BLAST_RADIUS_MAP = {
    "Brute Force Login": "Medium",
    "IDOR Access": "High",
    "Command Injection": "High",
    "Unrestricted File Upload": "Medium",
    "CSRF Transfer": "Medium",
}


def _map_to_frontend(entry):
    """Map backend experiment dict to frontend table schema."""
    attack = entry.get("attack_type", "unknown")
    success = entry.get("success", False)
    tte = entry.get("tte", 0.0)

    if success:
        status = "Failed"  # defense failed
    else:
        status = "Mitigated"

    if tte and tte > 0:
        time_str = f"{tte:.1f}s"
    else:
        time_str = "N/A"

    return {
        "target": attack,
        "blastRadius": BLAST_RADIUS_MAP.get(attack, "Medium"),
        "status": status,
        "timeToExploit": time_str,
        "enabled": True,   # always checked so toggles survive across runs
        "phase": entry.get("phase", "unknown"),
        "score": entry.get("score", 0),
        "enabled_controls": entry.get("enabled_controls", 0),
        "total_controls": entry.get("total_controls", 0),
    }


# ─── Existing Routes ───────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    for phase in ["before_chaos", "after_chaos"]:
        for exp in experiments[phase]:
            exp["score"] = calculate_resilience(
                exp.get("enabled_controls", 0), exp.get("total_controls", 1),
                exp.get("tte", 0), exp.get("success", False)
            )
    resp = make_response(render_template("index.html", results_before=experiments["before_chaos"], results_after=experiments["after_chaos"]))
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.route("/api/submit", methods=["POST"])
def receive_data():
    incoming_data = request.json
    phase = incoming_data.get("phase")

    if phase not in experiments:
        return jsonify({"error": "Invalid phase"}), 400

    # Calculate score
    incoming_data["score"] = calculate_resilience(
        incoming_data.get("enabled_controls", 0),
        incoming_data.get("total_controls", 1),
        incoming_data.get("tte", 0),
        incoming_data.get("success", False),
    )

    # Replace existing entry for same attack_type in this phase (upsert)
    attack_type = incoming_data.get("attack_type", "")
    existing = experiments[phase]
    replaced = False
    for i, entry in enumerate(existing):
        if entry.get("attack_type") == attack_type:
            existing[i] = incoming_data
            replaced = True
            break
    if not replaced:
        existing.append(incoming_data)

    save_experiment(phase, incoming_data)
    return jsonify({"message": "Data received successfully!", "status": "success"}), 200


@app.route("/api/experiments/clear", methods=["POST"])
def clear_experiments_endpoint():
    """Reset in-memory experiments for a fresh run."""
    from metrics_db import clear_experiments
    experiments["before_chaos"].clear()
    experiments["after_chaos"].clear()
    clear_experiments()
    return jsonify({"message": "Experiments cleared"}), 200


# ─── New Routes: Metrics API ───────────────────────────────────────────────

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """Return live experiment data mapped to frontend table schema.

    Deduplicates by attack_type only — one row per attack, most recent
    result wins. Phase is included as metadata but not used as a key,
    so the same attack never appears twice in the table.
    """
    seen = {}  # key: attack_type → latest entry across both phases
    for phase in ["before_chaos", "after_chaos"]:
        for exp in experiments[phase]:
            exp["phase"] = phase
            # Outcome-based score: blocked = 100, exploited = 0
            exp["score"] = 0.0 if exp.get("success", False) else 100.0
            key = exp.get("attack_type", "unknown")
            seen[key] = exp  # after_chaos overwrites before_chaos → latest wins

    return jsonify([_map_to_frontend(e) for e in seen.values()])


@app.route("/api/summary", methods=["GET"])
def get_summary():
    """Return aggregate baseline (before) and impact (after) scores.

    Resilience is outcome-based: (attacks_blocked / attacks_tested) * 100
      before_chaos all controls ON  -> all blocked    -> 100%
      after_chaos  all controls OFF -> some exploited -> e.g. 40%

    before.vulns = attack vectors probed in this run
    after.vulns  = attacks that successfully exploited the system
    """
    def calc_phase(phase):
        exps = experiments.get(phase, [])
        if not exps:
            return None

        tested    = len(exps)
        exploited = sum(1 for e in exps if e.get("success"))
        mitigated = tested - exploited
        resilience = round((mitigated / tested) * 100.0, 1)

        vulns = tested if phase == "before_chaos" else exploited

        return {
            "resilience": resilience,
            "vulns": vulns,
            "tested": tested,
            "exploited": exploited,
        }

    return jsonify({
        "before": calc_phase("before_chaos"),
        "after":  calc_phase("after_chaos")
    })


@app.route("/api/history", methods=["GET"])
def get_history():
    """Return full run history from Engine API."""
    try:
        resp = req_lib.get(f"{ENGINE_API_URL}/api/history", timeout=5)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify([])


# ─── New Routes: Orchestrator Proxy ─────────────────────────────────────────

@app.route("/api/execute", methods=["POST"])
def execute_chaos():
    """Proxy execution command to Engine API."""
    data = request.get_json(silent=True) or {}
    try:
        resp = req_lib.post(
            f"{ENGINE_API_URL}/api/execute",
            json=data,
            headers={"X-API-Key": ENGINE_API_KEY},
            timeout=10,
        )
        return jsonify(resp.json()), resp.status_code
    except req_lib.ConnectionError:
        return jsonify({"error": "Engine API unreachable", "message": "Is the Engine API server running on port 5002?"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stop", methods=["POST"])
def stop_chaos():
    """Proxy stop command to Engine API."""
    try:
        resp = req_lib.post(
            f"{ENGINE_API_URL}/api/stop",
            headers={"X-API-Key": ENGINE_API_KEY},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except req_lib.ConnectionError:
        return jsonify({"error": "Engine API unreachable"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/controls", methods=["POST"])
def proxy_controls():
    """Proxy security control toggles to Engine API."""
    data = request.get_json(silent=True) or {}
    try:
        resp = req_lib.post(
            f"{ENGINE_API_URL}/api/controls",
            json=data,
            headers={"X-API-Key": ENGINE_API_KEY},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except req_lib.ConnectionError:
        return jsonify({"error": "Engine API unreachable"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orchestrator/status", methods=["GET"])
def orchestrator_status():
    """Proxy status query to Engine API."""
    try:
        resp = req_lib.get(f"{ENGINE_API_URL}/api/status", timeout=5)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify({"status": "offline", "message": "Engine API not reachable"}), 200


@app.route("/api/attacks", methods=["GET"])
def list_attacks():
    """Proxy available attacks list from Engine API."""
    try:
        resp = req_lib.get(f"{ENGINE_API_URL}/api/attacks", timeout=5)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify({})


@app.route("/api/controls/status", methods=["GET"])
def controls_status():
    """Proxy control states from Engine API."""
    try:
        resp = req_lib.get(f"{ENGINE_API_URL}/api/controls/status", timeout=5)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify({"error": "Cannot query control states"}), 503


@app.route("/api/results", methods=["GET"])
def get_results():
    """Proxy persisted results from Engine API."""
    try:
        resp = req_lib.get(f"{ENGINE_API_URL}/api/results", timeout=5)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify([])


@app.route("/api/profiles", methods=["GET"])
def get_profiles():
    """Return saved security profiles."""
    return jsonify(load_profiles())


@app.route("/api/profiles", methods=["POST"])
def create_profile():
    """Save a security profile."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()                                                                                                                                                                                     
    controls = data.get("controls", {})

    if not name:
        return jsonify({"error": "Profile name required"}), 400

    save_profile(name, controls)
    return jsonify({"message": f"Profile '{name}' saved"}), 201


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
