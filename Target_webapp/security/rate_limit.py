import time
import app.config as config

login_attempts = {}

def check_rate_limit(ip):
    if not config.RATE_LIMIT_ENABLED:
        return True

    current_time = time.time()
    attempts = login_attempts.get(ip, [])

    attempts = [t for t in attempts if current_time - t < 60]

    if len(attempts) >= 5:
        return False

    attempts.append(current_time)
    login_attempts[ip] = attempts
    return True