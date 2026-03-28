from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- 1. METRICS SCORING LOGIC ---
def calculate_resilience(enabled_controls, total_controls, tte, is_success):
    defense_strength = enabled_controls / total_controls if total_controls > 0 else 0
    tte_normalized = min(tte / 10.0, 1.0)
    success_val = 1 if is_success else 0
    raw_score = (defense_strength * tte_normalized) / (success_val + 1)
    return round(raw_score * 100, 2)

# --- 2. SCEL DUMMY DATA ---
experiments = {
    "before_chaos": [
        {"attack_type": "SQLi (Login Bypass)", "enabled_controls": 5, "total_controls": 5, "tte": 15.0, "success": False},
        {"attack_type": "Brute Force (Admin)", "enabled_controls": 5, "total_controls": 5, "tte": 25.0, "success": False},
        {"attack_type": "XSS (Stored Payload)", "enabled_controls": 5, "total_controls": 5, "tte": 12.5, "success": False}
    ],
    "after_chaos": [
        {"attack_type": "SQLi (Sanitization Disabled)", "enabled_controls": 4, "total_controls": 5, "tte": 1.2, "success": True},
        {"attack_type": "Brute Force (Rate Limit Disabled)", "enabled_controls": 4, "total_controls": 5, "tte": 0.4, "success": True},
        {"attack_type": "IDOR Access (RBAC Disabled)", "enabled_controls": 3, "total_controls": 5, "tte": 2.1, "success": True}
    ]
}

# --- 3. HTML DASHBOARD ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SCEL Metrics Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px;}
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background-color: #2c3e50; color: white; }
        .score-high { color: #27ae60; font-weight: bold; }
        .score-low { color: #c0392b; font-weight: bold; }
        .success-true { color: #c0392b; font-weight: bold; } 
        .success-false { color: #27ae60; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ SCEL Resilience Dashboard</h1>
        <p>Measuring systemic security degradation.</p>

        <h2>Phase 1: Before Chaos (Baseline)</h2>
        <table>
            <tr><th>Attack Type</th><th>TTE (sec)</th><th>Exploit Success</th><th>Resilience Score (0-100)</th></tr>
            {% for row in results_before %}
            <tr>
                <td>{{ row.attack_type }}</td>
                <td>{{ row.tte }}s</td>
                <td class="{% if row.success %}success-true{% else %}success-false{% endif %}">{{ "Yes" if row.success else "No" }}</td>
                <td class="{% if row.score > 50 %}score-high{% else %}score-low{% endif %}">{{ row.score }}</td>
            </tr>
            {% endfor %}
        </table>

        <h2>Phase 2: After Chaos (Degraded Defenses)</h2>
        <table>
            <tr><th>Attack Type</th><th>TTE (sec)</th><th>Exploit Success</th><th>Resilience Score (0-100)</th></tr>
            {% for row in results_after %}
            <tr>
                <td>{{ row.attack_type }}</td>
                <td>{{ row.tte }}s</td>
                <td class="{% if row.success %}success-true{% else %}success-false{% endif %}">{{ "Yes" if row.success else "No" }}</td>
                <td class="{% if row.score > 50 %}score-high{% else %}score-low{% endif %}">{{ row.score }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route("/")
def dashboard():
    for phase in ["before_chaos", "after_chaos"]:
        for exp in experiments[phase]:
            exp["score"] = calculate_resilience(
                exp["enabled_controls"], exp["total_controls"], exp["tte"], exp["success"]
            )
    return render_template_string(HTML_TEMPLATE, results_before=experiments["before_chaos"], results_after=experiments["after_chaos"])

# --- 4. DATA RECEIVER (For Member 1 & 2 to connect to) ---
@app.route("/api/submit", methods=["POST"])
def receive_data():
    # Member 2's script will send data here in JSON format
    incoming_data = request.json
    phase = incoming_data.get("phase") # "before_chaos" or "after_chaos"
    
    if phase in experiments:
        experiments[phase].append(incoming_data)
        return jsonify({"message": "Data received successfully!", "status": "success"}), 200
    else:
        return jsonify({"error": "Invalid phase"}), 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
