import app.config as config

def sanitize_input(value):

    # Prevent None errors
    if value is None:
        return ""

    # Dynamic toggle check
    if not config.INPUT_SANITIZATION_ENABLED:
        return value

    # Simple sanitization
    return ''.join(e for e in value if e.isalnum())