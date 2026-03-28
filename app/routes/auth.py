from flask import Blueprint, request, session, jsonify
from app.models.users import USERS
from app.security.sanitization import sanitize_input
from app.security.rate_limit import check_rate_limit
from app.utils.logger import log_event
from flask import render_template, redirect, url_for

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    if request.is_json:
        data = request.json
        username = sanitize_input(data.get("username"))
        password = sanitize_input(data.get("password"))
    else:
        username = sanitize_input(request.form.get("username"))
        password = sanitize_input(request.form.get("password"))

    ip = request.remote_addr

    if not check_rate_limit(ip):
        log_event(f"Rate limit exceeded for IP {ip}")
        if request.is_json:
            return jsonify({"error": "Too many attempts"}), 429
        else:
            return render_template('login.html', message="Too many attempts ❌")

    user = USERS.get(username)

    if user and user["password"] == password:
        session['user_id'] = user["id"]
        log_event(f"User {username} logged in")

        if request.is_json:
            return jsonify({"message": "Login successful"})
        else:
            return redirect(f"/profile-ui/{user['id']}")

    log_event(f"Failed login attempt for {username}")

    if request.is_json:
        return jsonify({"error": "Invalid credentials"}), 401
    else:
        return render_template('login.html', message="Invalid credentials ❌")
@auth_bp.route('/')
def login_page():
    return render_template('login.html')

@auth_bp.route('/login-ui', methods=['POST'])
def login_ui():
    username = request.form.get("username")
    password = request.form.get("password")

    user = USERS.get(username)

    if user and user["password"] == password:
        session['user_id'] = user["id"]
        return redirect(f"/profile-ui/{user['id']}")

    return render_template('login.html', message="Invalid credentials")