from dataclasses import dataclass

CALCULATION_VERSION = "v1.1"


@dataclass(frozen=True)
class RecoveryValues:
    protein_low: int
    protein_high: int
    carbs_low: int
    carbs_high: int
    fluid_low: int | None
    fluid_high: int | None


def calculate_recovery(
    weight_kg: float,
    moving_seconds: int,
    intensity: str,
    pre_weight_kg: float | None,
    post_weight_kg: float | None,
) -> RecoveryValues:
    minutes = moving_seconds / 60
    if intensity == "low":
        carb_low, carb_high = 0.40, 0.60
    elif intensity == "moderate":
        carb_low, carb_high = 0.60, 0.80
    else:
        carb_low, carb_high = 0.80, 1.00
    if minutes >= 90 and intensity in {"moderate", "high"}:
        carb_low, carb_high = 1.00, 1.20

    protein_low = min(max(weight_kg * 0.25, 20), 40)
    protein_high = min(max(weight_kg * 0.40, 20), 40)
    fluid_low = fluid_high = None
    if pre_weight_kg is not None and post_weight_kg is not None:
        loss = max(pre_weight_kg - post_weight_kg, 0)
        fluid_low = round(loss * 1000 * 1.25)
        fluid_high = round(loss * 1000 * 1.50)
    return RecoveryValues(
        protein_low=round(protein_low),
        protein_high=round(protein_high),
        carbs_low=round(weight_kg * carb_low),
        carbs_high=round(weight_kg * carb_high),
        fluid_low=fluid_low,
        fluid_high=fluid_high,
    )

