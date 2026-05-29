from flask import Blueprint, session, jsonify, render_template, redirect
from app.security.rbac import check_access
from app.utils.logger import log_event
from app.models.users import USERS
import app.config as config

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile/<int:user_id>', methods=['GET'])
def profile(user_id):
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    logged_in_user = session['user_id']

    if not check_access(logged_in_user, user_id):
        log_event(f"Unauthorized access attempt by user {logged_in_user}")
        return jsonify({"error": "Access denied"}), 403

    log_event(f"User {logged_in_user} accessed profile {user_id}")
    return jsonify({"message": f"Profile data for user {user_id}"})


@profile_bp.route('/profile-ui/<int:user_id>')
def profile_ui(user_id):
    if 'user_id' not in session:
        return redirect('/')

    # Resolve user object for template hydration
    user = next((u for u in USERS.values() if u['id'] == user_id), None)

    # Session token for display in security panel
    session_token = session.get('csrf_token', 'N/A — no active CSRF token')

    log_event(f"User {session['user_id']} viewing profile-ui for {user_id}")

    return render_template(
        'profile.html',
        user_id=user_id,
        user=user,
        session_token=session_token,
        message="Profile loaded",
        rbac=config.RBAC_ENABLED,
        rate=config.RATE_LIMIT_ENABLED,
        sanitize=config.INPUT_SANITIZATION_ENABLED,
        csrf=config.CSRF_PROTECTION,
        idor=config.IDOR_PROTECTION,
        session_prot=config.SESSION_PROTECTION,
    )