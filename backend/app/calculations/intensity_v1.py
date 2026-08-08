CALCULATION_VERSION = "v1.1"


def classify_intensity(avg_heart_rate: float | None, age: int, met: float) -> str:
    if avg_heart_rate is not None and 30 <= avg_heart_rate <= 250:
        predicted_hr_max = 208 - (0.7 * age)
        fraction = avg_heart_rate / predicted_hr_max
        if fraction < 0.64:
            return "low"
        if fraction < 0.77:
            return "moderate"
        return "high"
    if met < 3.0:
        return "low"
    if met <= 6.0:
        return "moderate"
    return "high"

