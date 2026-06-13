"""
SCEL Resilience Scoring
========================
Severity-weighted resilience scoring inspired by OWASP Top 10 2021 and CVSS v3.1.

Formula
-------
    resilience = 100 − Σ weight[exploited attacks]

    The 100-point baseline represents a fully resilient system.
    Each exploited attack subtracts its weight. Unqueued attacks
    don't subtract anything — they haven't been proven broken.

Why severity-weighted?
    A flat 20% per attack treats Brute Force (slow, detectable) the same as
    Command Injection (instant RCE).  Severity weights mean that bypassing a
    CRITICAL control costs 3× more resilience than bypassing a MEDIUM one.

Attack weights (sum = 100 across all 5 attacks)
-----------------------------------------------
    Command Injection       CRITICAL  30   CVSS 9.8   OWASP A03:2021
    Unrestricted File Upload  HIGH    25   CVSS 8.8   OWASP A03:2021
    IDOR Access               HIGH    20   CVSS 7.5   OWASP A01:2021
    CSRF Transfer             MEDIUM  15   CVSS 6.5   OWASP A01:2021
    Brute Force Login         MEDIUM  10   CVSS 6.5   OWASP A07:2021

Example outcomes
-----------------
    All mitigated (any count)                    → 100 -  0 = 100.0%
    Only Command Injection exploited (w=30)      → 100 - 30 =  70.0%
    Only Unrestricted File Upload exploited (25) → 100 - 25 =  75.0%
    Only IDOR exploited (20)                     → 100 - 20 =  80.0%
    Only CSRF exploited (15)                     → 100 - 15 =  85.0%
    Only Brute Force exploited (10)              → 100 - 10 =  90.0%
    All 5 exploited                              → 100 -100 =   0.0%
"""

# ─── Severity registry ────────────────────────────────────────────────────────

ATTACK_SEVERITY = {
    "Command Injection": {
        "severity": "CRITICAL",
        "weight":   30,
        "cvss":     9.8,
        "owasp":    "A03:2021",
    },
    "Unrestricted File Upload": {
        "severity": "HIGH",
        "weight":   25,
        "cvss":     8.8,
        "owasp":    "A03:2021",
    },
    "IDOR Access": {
        "severity": "HIGH",
        "weight":   20,
        "cvss":     7.5,
        "owasp":    "A01:2021",
    },
    "CSRF Transfer": {
        "severity": "MEDIUM",
        "weight":   15,
        "cvss":     6.5,
        "owasp":    "A01:2021",
    },
    "Brute Force Login": {
        "severity": "MEDIUM",
        "weight":   10,
        "cvss":     6.5,
        "owasp":    "A07:2021",
    },
}

_DEFAULT = {"severity": "MEDIUM", "weight": 15, "cvss": 5.0, "owasp": "N/A"}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_weight(attack_type: str) -> int:
    """Return the severity weight (0-100 range) for an attack type."""
    return ATTACK_SEVERITY.get(attack_type, _DEFAULT)["weight"]


def get_severity(attack_type: str) -> str:
    """Return severity label: CRITICAL | HIGH | MEDIUM."""
    return ATTACK_SEVERITY.get(attack_type, _DEFAULT)["severity"]


def get_cvss(attack_type: str) -> float:
    """Return the CVSS v3.1 base score for an attack type."""
    return ATTACK_SEVERITY.get(attack_type, _DEFAULT)["cvss"]


def get_owasp(attack_type: str) -> str:
    """Return the OWASP Top 10 2021 category for an attack type."""
    return ATTACK_SEVERITY.get(attack_type, _DEFAULT)["owasp"]


# ─── Primary scoring function ─────────────────────────────────────────────────

def calculate_resilience_weighted(experiments: list) -> float:
    """Compute severity-weighted system resilience (0.0 – 100.0).

    Formula: resilience = 100 − Σ weight[exploited attacks]

    The 100-point baseline represents a fully resilient system. Each exploited
    attack subtracts its severity weight from that baseline. Attacks that were
    not queued don't subtract anything — they haven't been proven broken.

    Examples:
        All 5 run, all blocked          → 100 -  0 = 100.0%
        Only Brute Force exploited (10) → 100 - 10 =  90.0%
        Only Command Injection exploited→ 100 - 30 =  70.0%
        IDOR(20)+CSRF(15) both exploited→ 100 - 35 =  65.0%
        All 5 exploited                 → 100 -100 =   0.0%
    """
    if not experiments:
        return 100.0

    exploited_weight = sum(
        get_weight(e.get("attack_type", ""))
        for e in experiments
        if e.get("success", False)
    )

    return round(max(0.0, 100.0 - exploited_weight), 1)



# ─── Legacy shim ─────────────────────────────────────────────────────────────
# Kept so existing callers (app.py receive_data, dashboard route) don't break
# during the transition.  Will be removed once those callers are updated.

def calculate_resilience(enabled_controls, total_controls, tte, is_success):
    """Legacy control-based formula — no longer used for summary or table scores.

    The primary scoring is now calculate_resilience_weighted().
    This shim is retained only for backward compatibility with receive_data()
    and the dashboard() template route.
    """
    defense_strength = enabled_controls / total_controls if total_controls > 0 else 0.0
    raw_score = defense_strength * 100.0 if not is_success else defense_strength * 20.0
    return round(min(raw_score, 100.0), 1)
