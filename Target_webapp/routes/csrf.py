from flask import Blueprint, render_template, request, session, redirect
import secrets
import app.config as config
from app.models.users import USERS
from app.security.session_guard import has_valid_session_token

csrf_bp = Blueprint('csrf', __name__)


# =========================================
# TRANSFER PAGE
# =========================================

@csrf_bp.route('/transfer-page')
def transfer_page():
    if 'user_id' not in session:
        return redirect('/')

    if not has_valid_session_token(session):
        session.clear()
        return redirect('/')

    # Fetch logged-in user for balance display
    user_id = session['user_id']
    user = next((u for u in USERS.values() if u['id'] == user_id), None)
    balance = user['balance'] if user else 0

    # Generate CSRF token in secure mode
    if config.CSRF_PROTECTION:
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(16)

    return render_template(
        'transfer.html',
        csrf=config.CSRF_PROTECTION,
        csrf_token=session.get('csrf_token'),
        balance=balance,
    )


# =========================================
# MONEY TRANSFER
# =========================================

@csrf_bp.route('/transfer', methods=['POST'])
def transfer():
    if 'user_id' not in session:
        return redirect('/')

    if not has_valid_session_token(session):
        session.clear()
        return redirect('/')

    # =========================================
    # SECURE MODE — validate CSRF token
    # =========================================
    if config.CSRF_PROTECTION:
        submitted_token = request.form.get("csrf_token")
        session_token = session.get("csrf_token")

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
    # PROCESS TRANSFER
    # =========================================
    amount = request.form.get("amount", 0)
    recipient = request.form.get("recipient", "unknown")

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
        return render_template(
            'transfer.html',
            csrf=config.CSRF_PROTECTION,
            csrf_token=session.get('csrf_token'),
            balance=0,
            error="Invalid amount.",
        )

    # Rotate CSRF token after successful use (token rotation)
    if config.CSRF_PROTECTION:
        session['csrf_token'] = secrets.token_hex(16)

    return render_template(
        'transfer.html',
        csrf=config.CSRF_PROTECTION,
        csrf_token=session.get('csrf_token'),
        balance=0,
        success=f"✅ Transfer of ${amount:.2f} to '{recipient}' completed.",
    )


# =========================================
# ATTACKER PAGE
# =========================================

@csrf_bp.route('/attacker')
def attacker():
    return render_template('attacker.html')
