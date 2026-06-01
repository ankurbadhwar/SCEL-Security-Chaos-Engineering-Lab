def calculate_resilience(enabled_controls, total_controls, tte, is_success):
    """Calculate a resilience score (0-100) for a single attack result.

    Scoring logic:
      - defense_strength (0.0-1.0): ratio of enabled controls to total controls.
      - Attack BLOCKED  → score = defense_strength * 100
          All 6 controls active, attack fails → 6/6 * 100 = 100%
          3 of 6 controls active, attack fails → 3/6 * 100 = 50%
      - Attack SUCCEEDED → score = defense_strength * 20
          0 controls active, attack succeeds  → 0/6 * 20 = 0%
          3 controls active but still bypassed → 3/6 * 20 = 10%

    Expected ranges:
      Before chaos (all 6 controls ON, attacks blocked):   ~100%
      After chaos  (all 6 controls OFF, attacks succeed):  ~0%
    """
    defense_strength = enabled_controls / total_controls if total_controls > 0 else 0.0

    if not is_success:
        # Attack was fully blocked — resilience directly proportional to active controls
        raw_score = defense_strength * 100.0
    else:
        # Attack broke through — heavy penalty, small residual for partial controls
        raw_score = defense_strength * 20.0

    return round(min(raw_score, 100.0), 1)

