from app.calculations.energy_v1 import estimate_net_calories
from app.calculations.recovery_v1 import calculate_recovery
from app.calculations.intensity_v1 import classify_intensity
from app.services.food_matching import foods_match


class StubSemanticMatcher:
    def match(self, candidates, references):
        pairs = {
            ("chicken", "chicken breast"),
            ("steak", "rib eye"),
            ("chicken", "chiken legs"),
        }
        return {candidate: {reference for reference in references if (candidate, reference) in pairs} for candidate in candidates}


def test_intensity_hr_takes_precedence_over_met():
    assert classify_intensity(100, 40, 12) == "low"
    assert classify_intensity(None, 40, 12) == "high"


def test_energy_grows_with_weight_and_duration():
    short = estimate_net_calories(8, 70, 1800)
    long = estimate_net_calories(8, 70, 3600)
    heavy = estimate_net_calories(8, 90, 1800)
    assert long[1] > short[1]
    assert heavy[1] > short[1]


def test_recovery_rounds_and_uses_measured_fluid_loss():
    result = calculate_recovery(81.6, 90 * 60, "moderate", 81.6, 80.9)
    assert result.protein_low == 20
    assert result.protein_high == 33
    assert result.carbs_low == 82
    assert result.carbs_high == 98
    assert result.fluid_low == 875
    assert result.fluid_high == 1050


def test_recovery_fluid_is_null_without_weights():
    result = calculate_recovery(70, 30 * 60, "low", None, None)
    assert result.fluid_low is None
    assert result.fluid_high is None


def test_food_category_matching():
    matcher = StubSemanticMatcher()
    assert foods_match("chicken", "chicken breast", matcher)
    assert foods_match("steak", "rib eye", matcher)
    assert foods_match("chicken", "chiken legs", matcher)
    assert not foods_match("rice", "chicken breast", matcher)
