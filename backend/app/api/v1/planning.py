from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.ai.food_matcher import get_food_matcher
from app.ai.meal_generator import get_meal_generator
from app.api.errors import ApiError
from app.api.v1.profile import current_profile
from app.db.session import get_db
from app.models import GroceryLine, PlannedWorkout
from app.schemas.planning import (
    GroceryLineCheck,
    PlannedMealSubstitution,
    PlannedWorkoutCreate,
    PlannedWorkoutResponse,
    PlannedWorkoutUpdate,
    SubstitutionSuggestionsResponse,
    WeeklyPlanResponse,
)
from app.services.weekly_planning import (
    apply_substitution,
    assert_in_active_window,
    current_plan_start,
    generate_meal_options,
    get_or_create_plan,
    get_planned_meal,
    get_planned_workout,
    normalize_activity,
    plan_response,
    planned_workout_response,
    substitution_suggestions,
    synchronize_groceries,
)

router = APIRouter(prefix="/plan", tags=["planning"])


@router.get("", response_model=WeeklyPlanResponse)
def read_plan(db: Session = Depends(get_db)):
    profile = current_profile(db)
    plan = get_or_create_plan(db, profile)
    synchronize_groceries(db, profile, plan, get_food_matcher())
    db.commit()
    db.refresh(plan)
    return plan_response(profile, plan)


@router.post("/workouts", response_model=PlannedWorkoutResponse, status_code=201)
def create_planned_workout(payload: PlannedWorkoutCreate, db: Session = Depends(get_db)):
    profile = current_profile(db)
    plan = get_or_create_plan(db, profile)
    assert_in_active_window(plan, payload.scheduled_for)
    workout = PlannedWorkout(
        weekly_plan_id=plan.id,
        scheduled_for=payload.scheduled_for,
        activity_type=normalize_activity(payload.display_activity),
        display_activity=payload.display_activity,
        normalized_activity=normalize_activity(payload.display_activity),
        duration_seconds=payload.duration_minutes * 60,
        expected_intensity=payload.expected_intensity,
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return planned_workout_response(profile, workout)


@router.put("/workouts/{workout_id}", response_model=PlannedWorkoutResponse)
def update_planned_workout(workout_id: UUID, payload: PlannedWorkoutUpdate, db: Session = Depends(get_db)):
    profile = current_profile(db)
    workout = get_planned_workout(db, profile, workout_id)
    assert_in_active_window(workout.weekly_plan, payload.scheduled_for)
    workout.scheduled_for = payload.scheduled_for
    workout.activity_type = normalize_activity(payload.display_activity)
    workout.display_activity = payload.display_activity
    workout.normalized_activity = normalize_activity(payload.display_activity)
    workout.duration_seconds = payload.duration_minutes * 60
    workout.expected_intensity = payload.expected_intensity
    workout.meal_options.clear()
    db.flush()
    synchronize_groceries(db, profile, workout.weekly_plan, get_food_matcher())
    db.commit()
    db.refresh(workout)
    return planned_workout_response(profile, workout)


@router.delete("/workouts/{workout_id}", status_code=204)
def delete_planned_workout(workout_id: UUID, db: Session = Depends(get_db)):
    profile = current_profile(db)
    workout = get_planned_workout(db, profile, workout_id)
    plan = workout.weekly_plan
    db.delete(workout)
    db.flush()
    synchronize_groceries(db, profile, plan, get_food_matcher())
    db.commit()


@router.post("/workouts/{workout_id}/meal-options", response_model=PlannedWorkoutResponse)
def create_planned_meal_options(workout_id: UUID, db: Session = Depends(get_db)):
    profile = current_profile(db)
    workout = get_planned_workout(db, profile, workout_id)
    selected = next((option for option in workout.meal_options if option.selected), None)
    if selected is None:
        workout.meal_options.clear()
    else:
        for option in list(workout.meal_options):
            if option.id != selected.id:
                db.delete(option)
    db.flush()
    generated = generate_meal_options(profile, workout, profile.inventory, get_meal_generator(), get_food_matcher())
    if selected is not None:
        generated = [option for option in generated if option.name.casefold() != selected.name.casefold()]
    db.add_all(generated)
    db.commit()
    db.refresh(workout)
    return planned_workout_response(profile, workout)


@router.post("/meal-options/{meal_id}/select", response_model=WeeklyPlanResponse)
def select_planned_meal(meal_id: UUID, db: Session = Depends(get_db)):
    profile = current_profile(db)
    meal = get_planned_meal(db, profile, meal_id)
    for option in meal.planned_workout.meal_options:
        option.selected = False
        option.selected_at = None
    from datetime import datetime, timezone

    meal.selected = True
    meal.selected_at = datetime.now(timezone.utc)
    plan = meal.planned_workout.weekly_plan
    synchronize_groceries(db, profile, plan, get_food_matcher())
    db.commit()
    db.refresh(plan)
    return plan_response(profile, plan)


@router.get("/meal-options/{meal_id}/substitutions", response_model=SubstitutionSuggestionsResponse)
def list_substitutions(meal_id: UUID, ingredient_name: str, db: Session = Depends(get_db)):
    profile = current_profile(db)
    meal = get_planned_meal(db, profile, meal_id)
    return SubstitutionSuggestionsResponse(
        ingredient_name=ingredient_name,
        suggestions=substitution_suggestions(profile, meal, ingredient_name),
    )


@router.post("/meal-options/{meal_id}/substitutions", response_model=WeeklyPlanResponse)
def replace_planned_ingredient(meal_id: UUID, payload: PlannedMealSubstitution, db: Session = Depends(get_db)):
    profile = current_profile(db)
    meal = get_planned_meal(db, profile, meal_id)
    suggestions = substitution_suggestions(profile, meal, payload.ingredient_name)
    apply_substitution(meal, payload.ingredient_name, payload.replacement_name, suggestions)
    flag_modified(meal, "ingredients")
    plan = meal.planned_workout.weekly_plan
    synchronize_groceries(db, profile, plan, get_food_matcher())
    db.commit()
    db.refresh(plan)
    return plan_response(profile, plan)


@router.patch("/grocery-lines/{line_id}", response_model=WeeklyPlanResponse)
def check_grocery_line(line_id: UUID, payload: GroceryLineCheck, db: Session = Depends(get_db)):
    profile = current_profile(db)
    line = (
        db.query(GroceryLine)
        .filter(GroceryLine.id == line_id, GroceryLine.weekly_plan.has(profile_id=profile.id))
        .first()
    )
    if line is None:
        raise ApiError(404, "GROCERY_LINE_NOT_FOUND", "Grocery list item not found.")
    if line.available_at_home:
        raise ApiError(422, "PANTRY_ITEM_NOT_SHOPPABLE", "Items already at home cannot be checked off a grocery list.")
    line.checked = payload.checked
    db.commit()
    return plan_response(profile, line.weekly_plan)