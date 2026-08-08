CALCULATION_VERSION = "v1.1"


def estimate_net_calories(met: float, weight_kg: float, moving_seconds: int) -> tuple[int, int]:
    minutes = moving_seconds / 60
    midpoint = max(met - 1.0, 0) * 3.5 * weight_kg / 200 * minutes
    return round(midpoint * 0.80), round(midpoint * 1.20)

