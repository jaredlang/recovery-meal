from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.ai.food_matcher import FoodMatcher, get_food_matcher
from app.ai.meal_generator import MealGenerator, get_meal_generator
from app.api.errors import ApiError
from app.calculations.recovery_v1 import calculate_recovery
from app.models import GroceryLine, InventoryItem, PlannedMealOption, PlannedWorkout, RecoveryTarget, UserProfile, WeeklyPlan
from app.schemas.planning import GroceryLineResponse, PlannedMealResponse, PlannedRecoveryTarget, PlannedWorkoutResponse, SubstitutionSuggestion
from app.schemas.recommendation import MealIngredient
from app.schemas.workout import RangeResponse
from app.services.food_matching import match_foods, normalize_food
from app.services.recommendation_service import _validate_candidates, build_context, score_meal


SHOPPING_CATEGORIES = ("Produce", "Protein", "Grains and Bakery", "Dairy and Alternatives", "Pantry", "Frozen", "Other")


def normalize_activity(display_activity: str) -> str:
    activity = normalize_food(display_activity)
    if any(word in activity for word in ("run", "jog")):
        return "running"
    if any(word in activity for word in ("ride", "cycling", "cycle", "bike")):
        return "cycling"
    if "hike" in activity:
        return "hiking"
    if "walk" in activity:
        return "walking"
    return "unknown"


def current_plan_start() -> date:
    return datetime.now(timezone.utc).date()


def get_or_create_plan(db: Session, profile: UserProfile, starts_on: date | None = None) -> WeeklyPlan:
    starts_on = starts_on or current_plan_start()
    plan = db.query(WeeklyPlan).filter_by(profile_id=profile.id, starts_on=starts_on).first()
    if plan is None:
        plan = WeeklyPlan(profile_id=profile.id, starts_on=starts_on)
        db.add(plan)
        db.flush()
    return plan


def get_planned_workout(db: Session, profile: UserProfile, workout_id) -> PlannedWorkout:
    workout = (
        db.query(PlannedWorkout)
        .join(WeeklyPlan)
        .filter(PlannedWorkout.id == workout_id, WeeklyPlan.profile_id == profile.id)
        .first()
    )
    if workout is None:
        raise ApiError(404, "PLANNED_WORKOUT_NOT_FOUND", "Planned workout not found.")
    return workout


def get_planned_meal(db: Session, profile: UserProfile, meal_id) -> PlannedMealOption:
    meal = (
        db.query(PlannedMealOption)
        .join(PlannedWorkout)
        .join(WeeklyPlan)
        .filter(PlannedMealOption.id == meal_id, WeeklyPlan.profile_id == profile.id)
        .first()
    )
    if meal is None:
        raise ApiError(404, "PLANNED_MEAL_NOT_FOUND", "Planned meal not found.")
    return meal


def assert_in_active_window(plan: WeeklyPlan, scheduled_for: date) -> None:
    if not plan.starts_on <= scheduled_for <= plan.starts_on + timedelta(days=6):
        raise ApiError(422, "OUTSIDE_PLANNING_WINDOW", "Planned workouts must fall within the next seven days.")


def recovery_target(profile: UserProfile, workout: PlannedWorkout) -> PlannedRecoveryTarget | None:
    if workout.expected_intensity == "low":
        return None
    values = calculate_recovery(profile.weight_kg, workout.duration_seconds, workout.expected_intensity, None, None)
    return PlannedRecoveryTarget(
        protein_g=RangeResponse(low=values.protein_low, high=values.protein_high),
        carbs_g=RangeResponse(low=values.carbs_low, high=values.carbs_high),
    )


def planned_meal_response(meal: PlannedMealOption) -> PlannedMealResponse:
    return PlannedMealResponse(
        id=meal.id,
        category=meal.category,
        name=meal.name,
        ingredients=[MealIngredient.model_validate(item) for item in meal.ingredients],
        preparation_steps=meal.preparation_steps,
        prep_minutes=meal.prep_minutes,
        estimated_calories=meal.estimated_calories,
        protein_g=meal.protein_g,
        carbs_g=meal.carbs_g,
        fat_g=meal.fat_g,
        rationale=meal.rationale,
        recovery_match_score=meal.recovery_match_score,
        selected=meal.selected,
        selected_at=meal.selected_at,
    )


def planned_workout_response(profile: UserProfile, workout: PlannedWorkout) -> PlannedWorkoutResponse:
    target = recovery_target(profile, workout)
    selected = next((meal for meal in workout.meal_options if meal.selected), None)
    return PlannedWorkoutResponse(
        id=workout.id,
        scheduled_for=workout.scheduled_for,
        activity_type=workout.activity_type,
        display_activity=workout.display_activity,
        normalized_activity=workout.normalized_activity,
        duration_minutes=round(workout.duration_seconds / 60),
        expected_intensity=workout.expected_intensity,
        recovery_target=target,
        needs_meal_selection=target is not None and selected is None,
        meal_options=[planned_meal_response(meal) for meal in sorted(workout.meal_options, key=lambda item: item.created_at)],
    )


def category_for(name: str) -> str:
    key = normalize_food(name)
    if any(word in key for word in ("chicken", "turkey", "beef", "pork", "fish", "salmon", "tuna", "tofu", "tempeh", "egg", "protein")):
        return "Protein"
    if any(word in key for word in ("apple", "banana", "berry", "fruit", "spinach", "broccoli", "tomato", "pepper", "onion", "potato", "vegetable")):
        return "Produce"
    if any(word in key for word in ("rice", "oat", "bread", "pasta", "quinoa", "cereal", "tortilla")):
        return "Grains and Bakery"
    if any(word in key for word in ("milk", "yogurt", "cheese", "kefir")):
        return "Dairy and Alternatives"
    if any(word in key for word in ("frozen", "ice")):
        return "Frozen"
    if any(word in key for word in ("oil", "bean", "lentil", "nut", "seed", "sauce", "spice", "flour")):
        return "Pantry"
    return "Other"


def synchronize_groceries(db: Session, profile: UserProfile, plan: WeeklyPlan, matcher: FoodMatcher | None = None) -> None:
    grouped: dict[str, dict] = {}
    for workout in plan.planned_workouts:
        selected = next((meal for meal in workout.meal_options if meal.selected), None)
        if selected is None:
            continue
        for ingredient in selected.ingredients:
            name = ingredient["name"]
            unit = ingredient["unit"]
            identity_key = f"{normalize_food(name)}|{normalize_food(unit)}"
            if identity_key not in grouped:
                grouped[identity_key] = {"name": name, "normalized_name": normalize_food(name), "quantity": 0.0, "unit": unit}
            grouped[identity_key]["quantity"] += float(ingredient["quantity"])

    matches = match_foods([item["name"] for item in grouped.values()], [item.name for item in profile.inventory], matcher)
    existing = {line.identity_key: line for line in plan.grocery_lines}
    for identity_key, ingredient in grouped.items():
        line = existing.pop(identity_key, None)
        available_at_home = matches.has_match(ingredient["name"])
        if line is None:
            line = GroceryLine(weekly_plan_id=plan.id, identity_key=identity_key)
            db.add(line)
        line.name = ingredient["name"]
        line.normalized_name = ingredient["normalized_name"]
        line.quantity = ingredient["quantity"]
        line.unit = ingredient["unit"]
        line.category = category_for(line.name)
        line.available_at_home = available_at_home
        if available_at_home:
            line.checked = False
    for line in existing.values():
        db.delete(line)
    db.flush()


def grocery_line_response(line: GroceryLine) -> GroceryLineResponse:
    return GroceryLineResponse(
        id=line.id,
        name=line.name,
        quantity=line.quantity,
        unit=line.unit,
        category=line.category,
        available_at_home=line.available_at_home,
        checked=line.checked,
    )


def plan_response(profile: UserProfile, plan: WeeklyPlan):
    from app.schemas.planning import WeeklyPlanResponse

    return WeeklyPlanResponse(
        starts_on=plan.starts_on,
        ends_on=plan.starts_on + timedelta(days=6),
        workouts=[planned_workout_response(profile, workout) for workout in sorted(plan.planned_workouts, key=lambda item: (item.scheduled_for, item.created_at))],
        grocery_lines=[grocery_line_response(line) for line in sorted(plan.grocery_lines, key=lambda item: (item.available_at_home, SHOPPING_CATEGORIES.index(item.category), item.name))],
    )


def generate_meal_options(profile: UserProfile, workout: PlannedWorkout, inventory: list[InventoryItem], generator: MealGenerator | None = None, matcher: FoodMatcher | None = None) -> list[PlannedMealOption]:
    if workout.expected_intensity == "low":
        raise ApiError(422, "MEAL_NOT_NEEDED", "Low-intensity planned workouts do not need recovery meal suggestions.")
    values = calculate_recovery(profile.weight_kg, workout.duration_seconds, workout.expected_intensity, None, None)
    target = RecoveryTarget(
        workout_id=uuid4(),
        protein_g_low=values.protein_low,
        protein_g_high=values.protein_high,
        carbs_g_low=values.carbs_low,
        carbs_g_high=values.carbs_high,
        fluid_ml_low=None,
        fluid_ml_high=None,
        calculation_version="planned-v1",
    )
    context_workout = type("PlannedWorkoutContext", (), {"activity_type": workout.normalized_activity, "duration_seconds": workout.duration_seconds, "distance_meters": None, "intensity": workout.expected_intensity})()
    context = build_context(profile, context_workout, target, inventory)
    engine = generator or get_meal_generator()
    food_matcher = matcher or get_food_matcher()
    valid = _validate_candidates(engine.generate(context), context, profile, food_matcher)
    for candidate in valid:
        candidate.score = score_meal(candidate, target, profile)
    selected: list[tuple[str, object]] = []
    used_names: set[str] = set()
    for category, ordered in (
        ("best_recovery_match", sorted(valid, key=lambda item: item.score, reverse=True)),
        ("fastest", sorted(valid, key=lambda item: (item.candidate.prep_minutes, -item.score))),
        ("best_use_of_inventory", sorted(valid, key=lambda item: (item.inventory_coverage, item.score), reverse=True)),
    ):
        for candidate in ordered:
            key = normalize_food(candidate.candidate.name)
            if key not in used_names:
                selected.append((category, candidate))
                used_names.add(key)
                break
    return [
        PlannedMealOption(
            planned_workout_id=workout.id,
            category=category,
            name=candidate.candidate.name,
            ingredients=[ingredient.model_dump() for ingredient in candidate.ingredients],
            preparation_steps=candidate.candidate.preparation_steps,
            prep_minutes=candidate.candidate.prep_minutes,
            estimated_calories=round(4 * candidate.candidate.protein_g + 4 * candidate.candidate.carbs_g + 9 * candidate.candidate.fat_g),
            protein_g=candidate.candidate.protein_g,
            carbs_g=candidate.candidate.carbs_g,
            fat_g=candidate.candidate.fat_g,
            rationale=candidate.candidate.rationale,
            recovery_match_score=candidate.score,
        )
        for category, candidate in selected
    ]


SUBSTITUTIONS = {
    "chicken": [("turkey breast", "Similar lean protein with a longer fridge life."), ("firm tofu", "Plant-based protein that keeps well unopened.")],
    "chicken breast": [("turkey breast", "Similar lean protein with a longer fridge life."), ("firm tofu", "Plant-based protein that keeps well unopened.")],
    "rice": [("quinoa", "A quick-cooking grain with added protein."), ("whole wheat couscous", "A faster-cooking carbohydrate source.")],
    "milk": [("shelf-stable soy milk", "Keeps longer unopened and adds protein."), ("oat milk", "A shelf-stable alternative with similar preparation time.")],
    "banana": [("apple", "Keeps longer at room temperature."), ("frozen berries", "Keeps longer and needs no chopping.")],
}


def substitution_suggestions(profile: UserProfile, meal: PlannedMealOption, ingredient_name: str) -> list[SubstitutionSuggestion]:
    ingredient = next((item for item in meal.ingredients if normalize_food(item["name"]) == normalize_food(ingredient_name)), None)
    if ingredient is None:
        raise ApiError(404, "INGREDIENT_NOT_FOUND", "Ingredient not found in this planned meal.")
    suggestions = SUBSTITUTIONS.get(normalize_food(ingredient["name"]), [])
    avoided = {normalize_food(food) for food in profile.foods_to_avoid}
    favorites = {normalize_food(food) for food in profile.favorite_foods}
    response = [SubstitutionSuggestion(name=name, reason=reason) for name, reason in suggestions if normalize_food(name) not in avoided]
    return sorted(response, key=lambda item: normalize_food(item.name) not in favorites)


def apply_substitution(meal: PlannedMealOption, ingredient_name: str, replacement_name: str, allowed: list[SubstitutionSuggestion]) -> None:
    replacement = next((item for item in allowed if normalize_food(item.name) == normalize_food(replacement_name)), None)
    if replacement is None:
        raise ApiError(422, "INVALID_SUBSTITUTION", "Choose one of the suggested substitutions.")
    for ingredient in meal.ingredients:
        if normalize_food(ingredient["name"]) == normalize_food(ingredient_name):
            ingredient["name"] = replacement.name
            ingredient["available"] = False
            break
    else:
        raise ApiError(404, "INGREDIENT_NOT_FOUND", "Ingredient not found in this planned meal.")