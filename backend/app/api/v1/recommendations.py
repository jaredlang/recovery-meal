from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.ai.meal_image import get_meal_image_generator
from app.api.v1.profile import current_profile
from app.api.v1.workouts import meal_response
from app.models import FavoriteMeal, MealRecommendation
from app.schemas.recommendation import FavoriteResponse, MealResponse
from app.services.media import media_root, media_url

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendation(db: Session, recommendation_id: UUID) -> MealRecommendation:
    meal = db.query(MealRecommendation).filter_by(id=recommendation_id).first()
    if not meal:
        raise ApiError(404, "RECOMMENDATION_NOT_FOUND", "Recommendation not found.")
    return meal


def snapshot(meal: MealRecommendation) -> dict:
    return {
        "id": str(meal.id), "category": meal.category, "name": meal.name,
        "ingredients": meal.ingredients, "preparation_steps": meal.preparation_steps,
        "prep_minutes": meal.prep_minutes, "estimated_calories": meal.estimated_calories,
        "protein_g": meal.protein_g, "carbs_g": meal.carbs_g, "fat_g": meal.fat_g,
        "rationale": meal.rationale, "missing_ingredients": meal.missing_ingredients,
        "recovery_match_score": meal.recovery_match_score,
    }


@router.get("/{recommendation_id}", response_model=MealResponse)
def read_recommendation(recommendation_id: UUID, db: Session = Depends(get_db)):
    return meal_response(get_recommendation(db, recommendation_id), db)


@router.post("/{recommendation_id}/select")
def select_recommendation(recommendation_id: UUID, db: Session = Depends(get_db)):
    meal = get_recommendation(db, recommendation_id)
    db.query(MealRecommendation).filter_by(workout_id=meal.workout_id).update({"selected": False, "selected_at": None}, synchronize_session=False)
    meal.selected = True
    meal.selected_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": meal.id, "selected": True, "selected_at": meal.selected_at}


@router.post("/{recommendation_id}/favorite", response_model=FavoriteResponse)
def favorite_recommendation(recommendation_id: UUID, db: Session = Depends(get_db)):
    profile = current_profile(db)
    meal = get_recommendation(db, recommendation_id)
    favorite = db.query(FavoriteMeal).filter_by(profile_id=profile.id, recommendation_id=meal.id).first()
    if favorite is None:
        favorite = FavoriteMeal(profile_id=profile.id, recommendation_id=meal.id, snapshot=snapshot(meal), image_filename=meal.image_filename)
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
    return FavoriteResponse(id=favorite.id, recommendation_id=favorite.recommendation_id, meal=favorite.snapshot, image_url=media_url(favorite.image_filename), created_at=favorite.created_at)


@router.delete("/{recommendation_id}/favorite", status_code=204)
def unfavorite_recommendation(recommendation_id: UUID, db: Session = Depends(get_db)):
    profile = current_profile(db)
    favorite = db.query(FavoriteMeal).filter_by(profile_id=profile.id, recommendation_id=recommendation_id).first()
    if favorite is None:
        raise ApiError(404, "FAVORITE_NOT_FOUND", "Favorite meal not found.")
    db.delete(favorite)
    db.commit()


@router.post("/{recommendation_id}/image", response_model=MealResponse)
def generate_recommendation_image(recommendation_id: UUID, db: Session = Depends(get_db)):
    meal = get_recommendation(db, recommendation_id)
    if meal.image_status == "ready" and meal.image_filename:
        return meal_response(meal, db)
    if meal.image_status == "generating":
        raise ApiError(409, "IMAGE_IN_PROGRESS", "This meal image is already being generated.")
    meal.image_status = "generating"
    db.commit()
    try:
        generated = get_meal_image_generator().generate(meal.name, meal.ingredients)
        filename = f"meal-{meal.id}-{uuid4().hex[:8]}{generated.extension}"
        (media_root() / filename).write_bytes(generated.data)
        meal.image_filename = filename
        meal.image_status = "ready"
        for favorite in db.query(FavoriteMeal).filter_by(recommendation_id=meal.id).all():
            favorite.image_filename = filename
        db.commit()
        db.refresh(meal)
        return meal_response(meal, db)
    except Exception as exc:
        meal.image_status = "failed"
        db.commit()
        raise ApiError(502, "IMAGE_GENERATION_FAILED", "Meal image generation failed.") from exc

