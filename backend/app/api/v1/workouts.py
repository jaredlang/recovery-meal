from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.ai.meal_generator import get_meal_generator
from app.ai.food_matcher import get_food_matcher
from app.api.errors import ApiError
from app.api.v1.profile import current_profile
from app.calculations.met_v1 import met_for
from app.calculations.recovery_v1 import CALCULATION_VERSION, calculate_recovery
from app.db.session import get_db
from app.models import MealRecommendation, RecoveryTarget, UserProfile, Workout
from app.schemas.recommendation import MealResponse, RecommendationsResponse
from app.schemas.workout import RangeResponse, RecoveryResponse, WeightInput, WorkoutCorrection, WorkoutResponse
from app.services.recommendation_service import generate_recommendations
from app.services.workout_service import SUPPORTED_ACTIVITIES, calculate_fields, parse_gpx
from app.config import settings

router = APIRouter(prefix="/workouts", tags=["workouts"])


def get_workout(db: Session, workout_id: UUID) -> Workout:
    workout = db.query(Workout).filter_by(id=workout_id).first()
    if not workout:
        raise ApiError(404, "WORKOUT_NOT_FOUND", "Workout not found.")
    return workout


def workout_response(workout: Workout) -> WorkoutResponse:
    calories = None
    if workout.estimated_calories_low is not None and workout.estimated_calories_high is not None:
        calories = RangeResponse(low=workout.estimated_calories_low, high=workout.estimated_calories_high)
    return WorkoutResponse(
        id=workout.id,
        activity_type=workout.activity_type,
        started_at=workout.started_at,
        duration_seconds=workout.duration_seconds,
        moving_seconds=workout.moving_seconds,
        distance_meters=workout.distance_meters,
        elevation_gain_meters=workout.elevation_gain_meters,
        avg_speed_mps=workout.avg_speed_mps,
        avg_heart_rate=workout.avg_heart_rate,
        max_heart_rate=workout.max_heart_rate,
        intensity=workout.intensity,
        met_value=workout.met_value,
        estimated_calories=calories,
        source_filename=workout.source_filename,
    )


@router.post("", response_model=WorkoutResponse, status_code=201)
async def upload_workout(file: UploadFile = File(...), db: Session = Depends(get_db)):
    profile = current_profile(db)
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise ApiError(400, "GPX_TOO_LARGE", "The uploaded GPX file exceeds the 10 MB limit.")
    try:
        parsed = parse_gpx(content, file.filename or "workout.gpx", datetime.now(timezone.utc))
    except ValueError as exc:
        raise ApiError(400, "INVALID_GPX", str(exc)) from exc
    fields = calculate_fields(parsed, profile.age, profile.weight_kg)
    workout = Workout(
        profile_id=profile.id,
        activity_type=parsed.activity_type,
        started_at=parsed.started_at,
        duration_seconds=parsed.duration_seconds,
        moving_seconds=parsed.duration_seconds,
        distance_meters=parsed.distance_meters,
        elevation_gain_meters=parsed.elevation_gain_meters,
        avg_speed_mps=parsed.avg_speed_mps,
        avg_heart_rate=parsed.avg_heart_rate,
        max_heart_rate=parsed.max_heart_rate,
        source_filename=Path(file.filename or "workout.gpx").name,
        **fields,
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout_response(workout)


@router.get("/{workout_id}", response_model=WorkoutResponse)
def read_workout(workout_id: UUID, db: Session = Depends(get_db)):
    return workout_response(get_workout(db, workout_id))


@router.patch("/{workout_id}/correction", response_model=WorkoutResponse)
def correct_workout(workout_id: UUID, payload: WorkoutCorrection, db: Session = Depends(get_db)):
    workout = get_workout(db, workout_id)
    profile = current_profile(db)
    workout.activity_type = payload.activity_type
    workout.duration_seconds = payload.duration_seconds
    workout.moving_seconds = payload.duration_seconds
    workout.avg_speed_mps = workout.distance_meters / payload.duration_seconds if workout.distance_meters else None
    fields = calculate_fields(
        type("Parsed", (), {"activity_type": workout.activity_type, "duration_seconds": payload.duration_seconds, "avg_speed_mps": workout.avg_speed_mps, "avg_heart_rate": workout.avg_heart_rate})(),
        profile.age,
        profile.weight_kg,
    )
    for key, value in fields.items():
        setattr(workout, key, value)
    db.commit()
    db.refresh(workout)
    return workout_response(workout)


@router.post("/{workout_id}/recovery-target", response_model=RecoveryResponse)
def create_recovery_target(workout_id: UUID, payload: WeightInput, db: Session = Depends(get_db)):
    workout = get_workout(db, workout_id)
    profile = current_profile(db)
    if (payload.pre_exercise_weight_kg is None) != (payload.post_exercise_weight_kg is None):
        raise ApiError(422, "WEIGHT_PAIR_REQUIRED", "Provide both pre- and post-exercise weights, or neither.")
    if workout.activity_type not in SUPPORTED_ACTIVITIES or workout.moving_seconds is None or workout.intensity is None:
        raise ApiError(422, "CALCULATION_INPUT_INCOMPLETE", "Correct the activity and duration before calculating recovery.")
    workout.pre_exercise_weight_kg = payload.pre_exercise_weight_kg
    workout.post_exercise_weight_kg = payload.post_exercise_weight_kg
    values = calculate_recovery(profile.weight_kg, workout.moving_seconds, workout.intensity, payload.pre_exercise_weight_kg, payload.post_exercise_weight_kg)
    target = workout.recovery_target
    if target is None:
        target = RecoveryTarget(workout_id=workout.id)
        db.add(target)
    target.protein_g_low = values.protein_low
    target.protein_g_high = values.protein_high
    target.carbs_g_low = values.carbs_low
    target.carbs_g_high = values.carbs_high
    target.fluid_ml_low = values.fluid_low
    target.fluid_ml_high = values.fluid_high
    target.calculation_version = CALCULATION_VERSION
    db.commit()
    return RecoveryResponse(
        workout_id=workout.id,
        protein_g=RangeResponse(low=values.protein_low, high=values.protein_high),
        carbs_g=RangeResponse(low=values.carbs_low, high=values.carbs_high),
        fluid_ml=RangeResponse(low=values.fluid_low, high=values.fluid_high) if values.fluid_low is not None else None,
        calculation_version=CALCULATION_VERSION,
    )


def meal_response(meal: MealRecommendation) -> MealResponse:
    return MealResponse(
        id=meal.id,
        category=meal.category,
        name=meal.name,
        ingredients=meal.ingredients,
        preparation_steps=meal.preparation_steps,
        prep_minutes=meal.prep_minutes,
        estimated_calories=meal.estimated_calories,
        protein_g=meal.protein_g,
        carbs_g=meal.carbs_g,
        fat_g=meal.fat_g,
        rationale=meal.rationale,
        missing_ingredients=meal.missing_ingredients,
        recovery_match_score=meal.recovery_match_score,
        selected=meal.selected,
    )


@router.post("/{workout_id}/recommendations", response_model=RecommendationsResponse, status_code=201)
def create_recommendations(workout_id: UUID, db: Session = Depends(get_db)):
    workout = get_workout(db, workout_id)
    profile = current_profile(db)
    target = workout.recovery_target
    if target is None:
        raise ApiError(422, "RECOVERY_TARGET_REQUIRED", "Calculate the recovery target before requesting recommendations.")
    inventory = profile.inventory
    try:
        new_meals = generate_recommendations(db, profile, workout, target, inventory, get_meal_generator(), get_food_matcher())
    except Exception as exc:
        db.rollback()
        raise ApiError(502, "MEAL_GENERATION_FAILED", "Meal generation failed; no recommendations were changed.") from exc
    db.query(MealRecommendation).filter_by(workout_id=workout.id).delete(synchronize_session=False)
    db.add_all(new_meals)
    db.commit()
    for meal in new_meals:
        db.refresh(meal)
    return RecommendationsResponse(recommendations=[meal_response(meal) for meal in new_meals])


@router.get("/{workout_id}/recommendations", response_model=RecommendationsResponse)
def list_recommendations(workout_id: UUID, db: Session = Depends(get_db)):
    workout = get_workout(db, workout_id)
    meals = db.query(MealRecommendation).filter_by(workout_id=workout.id).order_by(MealRecommendation.created_at).all()
    return RecommendationsResponse(recommendations=[meal_response(meal) for meal in meals])
