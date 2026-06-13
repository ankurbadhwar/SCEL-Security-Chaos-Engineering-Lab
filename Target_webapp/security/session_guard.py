import secrets

import app.config as config


def issue_session_token():
    """Create a fresh session-bound token for authenticated users."""
    return secrets.token_hex(16)


def has_valid_session_token(session):
    """Require a session token only when session protection is enabled."""
    if not config.SESSION_PROTECTION:
        return True
    return bool(session.get("session_token"))


def get_session_token_display(session):
    """Show a stable UI value without leaking the real token in secure mode."""
    token = session.get("session_token")
    if not token:
        return "N/A - no active session token"
    if config.SESSION_PROTECTION:
        return f"{token[:8]}...{token[-4:]} (masked)"
    return token
