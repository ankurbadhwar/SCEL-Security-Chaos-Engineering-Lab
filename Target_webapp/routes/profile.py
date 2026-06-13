from flask import Blueprint, session, jsonify, render_template, redirect

import app.config as config
from app.models.users import USERS
from app.security.rbac import check_access
from app.security.session_guard import (
    get_session_token_display,
    has_valid_session_token,
)
from app.utils.logger import log_event

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile/<int:user_id>', methods=['GET'])
def profile(user_id):
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    logged_in_user = session['user_id']

    if not has_valid_session_token(session):
        log_event(f"Invalid session token for user {logged_in_user}")
        session.clear()
        return jsonify({"error": "Invalid session"}), 401

    if config.IDOR_PROTECTION and logged_in_user != user_id:
        log_event(f"IDOR protection blocked user {logged_in_user} from profile {user_id}")
        return jsonify({"error": "Access denied"}), 403

    if not check_access(logged_in_user, user_id):
        log_event(f"Unauthorized access attempt by user {logged_in_user}")
        return jsonify({"error": "Access denied"}), 403

    log_event(f"User {logged_in_user} accessed profile {user_id}")
    return jsonify({"message": f"Profile data for user {user_id}"})


@profile_bp.route('/profile-ui/<int:user_id>')
def profile_ui(user_id):
    if 'user_id' not in session:
        return redirect('/')

    logged_in_user = session['user_id']

    if not has_valid_session_token(session):
        log_event(f"Invalid session token for user {logged_in_user}")
        session.clear()
        return redirect('/')

    blocked = False
    resolved_user_id = user_id

    if config.IDOR_PROTECTION and logged_in_user != user_id:
        blocked = True
        resolved_user_id = logged_in_user
        log_event(f"IDOR protection blocked user {logged_in_user} from profile-ui {user_id}")
    elif not check_access(logged_in_user, user_id):
        blocked = True
        resolved_user_id = logged_in_user
        log_event(f"Unauthorized profile-ui access attempt by user {logged_in_user} for {user_id}")

    user = next((u for u in USERS.values() if u['id'] == resolved_user_id), None)
    session_token = get_session_token_display(session)

    log_event(f"User {logged_in_user} viewing profile-ui for {resolved_user_id}")

    return render_template(
        'profile.html',
        user_id=resolved_user_id,
        user=user,
        blocked=blocked,
        session_token=session_token,
        message="Profile loaded",
        rbac=config.RBAC_ENABLED,
        rate=config.RATE_LIMIT_ENABLED,
        sanitize=config.INPUT_SANITIZATION_ENABLED,
        csrf=config.CSRF_PROTECTION,
        idor=config.IDOR_PROTECTION,
        session_prot=config.SESSION_PROTECTION,
    )
