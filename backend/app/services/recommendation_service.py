from dataclasses import dataclass

from app.ai.meal_generator import MealGenerator
from app.ai.food_matcher import FoodMatcher
from app.models import InventoryItem, MealRecommendation, RecoveryTarget, UserProfile, Workout
from app.schemas.recommendation import MealCandidate, MealIngredient
from app.services.food_matching import FoodMatchTable, match_foods, normalize_food


@dataclass
class ValidatedMeal:
    candidate: MealCandidate
    ingredients: list[MealIngredient]
    missing: list[str]
    inventory_coverage: float
    favorite_match: bool
    score: float


def validate_candidate(
    candidate: MealCandidate,
    inventory_matches: FoodMatchTable,
    avoid_matches: FoodMatchTable,
    favorite_matches: FoodMatchTable,
    max_prep: int | None,
) -> ValidatedMeal | None:
    if max_prep is not None and candidate.prep_minutes > max_prep:
        return None
    if any(avoid_matches.has_match(ingredient.name) for ingredient in candidate.ingredients):
        return None
    ingredients: list[MealIngredient] = []
    missing: list[str] = []
    available_count = 0
    for ingredient in candidate.ingredients:
        available = inventory_matches.has_match(ingredient.name)
        if available:
            available_count += 1
        else:
            missing.append(ingredient.name)
        ingredients.append(ingredient.model_copy(update={"available": available}))
    coverage = available_count / len(ingredients)
    # Macro distance score is normalized later against the target range.
    return ValidatedMeal(candidate, ingredients, missing, coverage, any(favorite_matches.has_match(i.name) for i in candidate.ingredients), 0.0)


def score_meal(meal: ValidatedMeal, target: RecoveryTarget, profile: UserProfile) -> float:
    candidate = meal.candidate

    def range_distance(value: int, low: int, high: int) -> float:
        if low <= value <= high:
            return 0.0
        return (low - value) / max(low, 1) if value < low else (value - high) / max(high, 1)

    macro_distance = range_distance(candidate.protein_g, target.protein_g_low, target.protein_g_high) + range_distance(candidate.carbs_g, target.carbs_g_low, target.carbs_g_high)
    favorite_bonus = 0.08 if meal.favorite_match else 0.0
    goal_bonus = 0.04 if profile.fitness_goal == "lose_weight" and candidate.fat_g <= 20 else 0.0
    return round(max(0.0, 1.0 - min(macro_distance, 1.0)) + meal.inventory_coverage * 0.25 - candidate.prep_minutes / 1000 + favorite_bonus + goal_bonus, 4)


def build_context(profile: UserProfile, workout: Workout, target: RecoveryTarget, inventory: list[InventoryItem]) -> dict:
    return {
        "profile": {"age": profile.age, "sex": profile.sex, "weight_kg": profile.weight_kg, "fitness_goal": profile.fitness_goal},
        "workout": {"activity_type": workout.activity_type, "duration_seconds": workout.duration_seconds, "distance_meters": workout.distance_meters, "intensity": workout.intensity},
        "recovery_target": {"protein_g": {"low": target.protein_g_low, "high": target.protein_g_high}, "carbs_g": {"low": target.carbs_g_low, "high": target.carbs_g_high}},
        "foods_to_avoid": profile.foods_to_avoid,
        "favorite_foods": profile.favorite_foods,
        "available_foods": [item.name for item in inventory],
        "max_prep_minutes": profile.max_prep_minutes,
    }


def _validate_candidates(candidates: list[MealCandidate], context: dict, profile: UserProfile, matcher: FoodMatcher) -> list[ValidatedMeal]:
    candidate_names = list(dict.fromkeys(ingredient.name for candidate in candidates for ingredient in candidate.ingredients))
    inventory_matches = match_foods(candidate_names, context["available_foods"], matcher)
    avoid_matches = match_foods(candidate_names, profile.foods_to_avoid, matcher)
    favorite_matches = match_foods(candidate_names, profile.favorite_foods, matcher)
    return [
        meal
        for candidate in candidates
        if (meal := validate_candidate(candidate, inventory_matches, avoid_matches, favorite_matches, profile.max_prep_minutes))
    ]


def generate_recommendations(db, profile: UserProfile, workout: Workout, target: RecoveryTarget, inventory: list[InventoryItem], generator: MealGenerator, matcher: FoodMatcher) -> list[MealRecommendation]:
    context = build_context(profile, workout, target, inventory)
    candidates = generator.generate(context)
    valid = _validate_candidates(candidates, context, profile, matcher)
    if not valid:
        # One compact corrective retry is intentionally bounded.
        candidates = generator.generate({**context, "correction": "Return only candidates satisfying the hard prep and avoid-list constraints."})
        valid = _validate_candidates(candidates, context, profile, matcher)
    for meal in valid:
        meal.score = score_meal(meal, target, profile)

    selected: list[tuple[str, ValidatedMeal]] = []
    used: set[str] = set()
    for category, ordered in (
        ("best_recovery_match", sorted(valid, key=lambda item: item.score, reverse=True)),
        ("fastest", sorted(valid, key=lambda item: (item.candidate.prep_minutes, -item.score))),
        ("best_use_of_inventory", sorted(valid, key=lambda item: (item.inventory_coverage, item.score), reverse=True)),
    ):
        for meal in ordered:
            key = normalize_food(meal.candidate.name)
            if key not in used:
                selected.append((category, meal))
                used.add(key)
                break
        if len(selected) == 3:
            break

    return [
        MealRecommendation(
            workout_id=workout.id,
            category=category,
            name=meal.candidate.name,
            ingredients=[ingredient.model_dump() for ingredient in meal.ingredients],
            preparation_steps=meal.candidate.preparation_steps,
            prep_minutes=meal.candidate.prep_minutes,
            estimated_calories=round(4 * meal.candidate.protein_g + 4 * meal.candidate.carbs_g + 9 * meal.candidate.fat_g),
            protein_g=meal.candidate.protein_g,
            carbs_g=meal.candidate.carbs_g,
            fat_g=meal.candidate.fat_g,
            rationale=meal.candidate.rationale,
            missing_ingredients=meal.missing,
            recovery_match_score=meal.score,
        )
        for category, meal in selected
    ]
