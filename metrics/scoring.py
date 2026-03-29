def calculate_resilience(enabled_controls, total_controls, tte, is_success):
    defense_strength = enabled_controls / total_controls if total_controls > 0 else 0
    tte_normalized = min(tte / 10.0, 1.0)
    success_val = 1 if is_success else 0
    raw_score = (defense_strength * tte_normalized) / (success_val + 1)
    return round(raw_score * 100, 2)
