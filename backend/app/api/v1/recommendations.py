from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.models import MealRecommendation

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/{recommendation_id}/select")
def select_recommendation(recommendation_id: UUID, db: Session = Depends(get_db)):
    meal = db.query(MealRecommendation).filter_by(id=recommendation_id).first()
    if not meal:
        raise ApiError(404, "RECOMMENDATION_NOT_FOUND", "Recommendation not found.")
    db.query(MealRecommendation).filter_by(workout_id=meal.workout_id).update({"selected": False}, synchronize_session=False)
    meal.selected = True
    db.commit()
    return {"id": meal.id, "selected": True}

