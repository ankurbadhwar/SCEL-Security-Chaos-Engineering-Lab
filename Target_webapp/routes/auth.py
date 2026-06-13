from flask import Blueprint, request, session, jsonify, render_template, redirect

from app.models.users import USERS
from app.security.rate_limit import check_rate_limit
from app.security.sanitization import sanitize_input
from app.security.session_guard import issue_session_token
from app.utils.logger import log_event

auth_bp = Blueprint('auth', __name__)


def _get_sanitized_credentials():
    if request.is_json:
        data = request.json or {}
        username = sanitize_input(data.get("username"))
        password = sanitize_input(data.get("password"))
    else:
        username = sanitize_input(request.form.get("username"))
        password = sanitize_input(request.form.get("password"))
    return username, password


def _handle_login_success(user, username):
    session.clear()
    session['user_id'] = user["id"]
    session['session_token'] = issue_session_token()
    log_event(f"User {username} logged in")


@auth_bp.route('/login', methods=['POST'])
def login():
    username, password = _get_sanitized_credentials()
    ip = request.remote_addr

    if not check_rate_limit(ip):
        log_event(f"Rate limit exceeded for IP {ip}")
        if request.is_json:
            return jsonify({"error": "Too many attempts"}), 429
        return render_template('login.html', message="Too many attempts - try again later")

    user = USERS.get(username)

    if user and user["password"] == password:
        _handle_login_success(user, username)

        if request.is_json:
            return jsonify({"message": "Login successful"})
        return redirect(f"/profile-ui/{user['id']}")

    log_event(f"Failed login attempt for {username}")

    if request.is_json:
        return jsonify({"error": "Invalid credentials"}), 401
    return render_template('login.html', message="Invalid credentials")


@auth_bp.route('/')
def login_page():
    return render_template('login.html')


@auth_bp.route('/login-ui', methods=['POST'])
def login_ui():
    username, password = _get_sanitized_credentials()
    ip = request.remote_addr

    if not check_rate_limit(ip):
        log_event(f"Rate limit exceeded for IP {ip}")
        return render_template('login.html', message="Too many attempts - try again later")

    user = USERS.get(username)

    if user and user["password"] == password:
        _handle_login_success(user, username)
        return redirect(f"/profile-ui/{user['id']}")

    log_event(f"Failed login attempt for {username}")
    return render_template('login.html', message="Invalid credentials")
