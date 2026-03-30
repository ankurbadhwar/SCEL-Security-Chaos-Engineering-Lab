from flask import Flask, render_template, request, jsonify
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import sys
import os

# 1. Tell Python to look one folder up (in the Metrics folder)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. Import directly from your scoring.py file
from scoring import calculate_resilience

app = Flask(__name__)

experiments = {
    "before_chaos": [
        {"attack_type": "SQLi (Login Bypass)", "enabled_controls": 5, "total_controls": 5, "tte": 15.0, "success": False},
        {"attack_type": "Brute Force (Admin)", "enabled_controls": 5, "total_controls": 5, "tte": 25.0, "success": False}
    ],
    "after_chaos": [
        {"attack_type": "SQLi (Sanitization Disabled)", "enabled_controls": 4, "total_controls": 5, "tte": 1.2, "success": True},
        {"attack_type": "IDOR Access (RBAC Disabled)", "enabled_controls": 3, "total_controls": 5, "tte": 2.1, "success": True}
    ]
}

@app.route("/")
def dashboard():
    for phase in ["before_chaos", "after_chaos"]:
        for exp in experiments[phase]:
            exp["score"] = calculate_resilience(
                exp["enabled_controls"], exp["total_controls"], exp["tte"], exp["success"]
            )
    return render_template("index.html", results_before=experiments["before_chaos"], results_after=experiments["after_chaos"])

@app.route("/api/submit", methods=["POST"])
def receive_data():
    incoming_data = request.json
    phase = incoming_data.get("phase")
    
    if phase in experiments:
        experiments[phase].append(incoming_data)
        return jsonify({"message": "Data received successfully!", "status": "success"}), 200
    else:
        return jsonify({"error": "Invalid phase"}), 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
