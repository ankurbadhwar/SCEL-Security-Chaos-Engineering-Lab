from app.config import INPUT_SANITIZATION_ENABLED
import app.config as config

def sanitize_input(value):
    if not INPUT_SANITIZATION_ENABLED:
        return value
    return ''.join(e for e in value if e.isalnum())