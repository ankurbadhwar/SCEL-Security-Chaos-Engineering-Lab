from flask import Blueprint, request, jsonify, redirect

import app.config as config
from app.security.rate_limit import login_attempts

toggle_bp = Blueprint('toggle', __name__)

@toggle_bp.route('/toggle', methods=['POST'])
def toggle():
    data = request.json
    control = data.get("control")
    value = data.get("value")

    if hasattr(config, control):
        setattr(config, control, value)
        return jsonify({"message": f"{control} set to {value}"})

    return jsonify({"error": "Invalid control"}), 400

@toggle_bp.route('/toggle-ui', methods=['POST'])
def toggle_ui():
    control = request.form.get("control")

    if not hasattr(config, control):
        return redirect(request.referrer or '/')

    current = getattr(config, control)
    setattr(config, control, not current)

    return redirect(request.referrer or '/')

@toggle_bp.route('/reset-rate-limit', methods=['POST'])
def reset_rate_limit():
    """Clear all stored login attempts so rate limiting starts fresh."""
    login_attempts.clear()
    return jsonify({"message": "Rate limit counters cleared"})

@toggle_bp.route('/status', methods=['GET'])
def status():
    """Return current state of all security controls."""
    return jsonify({
        "RATE_LIMIT_ENABLED": config.RATE_LIMIT_ENABLED,
        "RBAC_ENABLED": config.RBAC_ENABLED,
        "INPUT_SANITIZATION_ENABLED": config.INPUT_SANITIZATION_ENABLED,
        "CSRF_PROTECTION": config.CSRF_PROTECTION,
        "IDOR_PROTECTION": config.IDOR_PROTECTION,
        "SESSION_PROTECTION": config.SESSION_PROTECTION,
    })
