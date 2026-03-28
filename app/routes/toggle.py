from flask import Blueprint, request, jsonify
import app.config as config
from flask import redirect, request

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

    current = getattr(config, control)
    setattr(config, control, not current)

    return redirect(request.referrer)