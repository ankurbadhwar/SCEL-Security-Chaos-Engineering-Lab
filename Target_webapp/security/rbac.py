import app.config as config
from app.config import RBAC_ENABLED

def check_access(logged_in_user, requested_user):
    if not config.RBAC_ENABLED:
        return True

    return logged_in_user == requested_user