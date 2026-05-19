from flask import Blueprint, render_template, request
from flask import session, redirect
import secrets
import app.config as config

csrf_bp = Blueprint('csrf', __name__)


# =========================================
# TRANSFER PAGE
# =========================================

@csrf_bp.route('/transfer-page')
def transfer_page():

    if 'user_id' not in session:
        return redirect('/')

    # ✅ Generate CSRF token in secure mode
    if config.CSRF_PROTECTION:

        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(16)

    return render_template(
        'transfer.html',
        csrf=config.CSRF_PROTECTION,
        csrf_token=session.get('csrf_token')
    )


# =========================================
# MONEY TRANSFER
# =========================================

@csrf_bp.route('/transfer', methods=['POST'])
def transfer():

    if 'user_id' not in session:
        return "Login required"

    # =========================================
    # SECURE MODE
    # =========================================

    if config.CSRF_PROTECTION:
        submitted_token = request.form.get("csrf_token")
        session_token = session.get("csrf_token")
        print("SUBMITTED TOKEN:", submitted_token)
        print("SESSION TOKEN:", session_token)

          # ❌ Block attack if:
          # - token missing
          # - session token missing
          # - token mismatch
        
    if (
        not submitted_token or
        not session_token or
        submitted_token != session_token
    ):

        return """
        <h2 style='color:red;text-align:center;margin-top:100px;'>
        ❌ CSRF ATTACK BLOCKED
        </h2>
        """

# =========================================
# ATTACKER PAGE
# =========================================

@csrf_bp.route('/attacker')
def attacker():

    return render_template('attacker.html')