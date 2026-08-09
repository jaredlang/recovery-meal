from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.profile import current_profile
from app.db.session import get_db
from app.models import FavoriteMeal
from app.schemas.recommendation import FavoriteResponse
from app.services.media import media_url

router = APIRouter(prefix="/favorites", tags=["favorites"])


def response(item: FavoriteMeal) -> FavoriteResponse:
    return FavoriteResponse(id=item.id, recommendation_id=item.recommendation_id, meal=item.snapshot, image_url=media_url(item.image_filename), created_at=item.created_at)


@router.get("", response_model=list[FavoriteResponse])
def list_favorites(db: Session = Depends(get_db)):
    profile = current_profile(db)
    items = db.query(FavoriteMeal).filter_by(profile_id=profile.id).order_by(FavoriteMeal.created_at.desc()).all()
    return [response(item) for item in items]


@router.get("/{favorite_id}", response_model=FavoriteResponse)
def read_favorite(favorite_id: UUID, db: Session = Depends(get_db)):
    profile = current_profile(db)
    item = db.query(FavoriteMeal).filter_by(id=favorite_id, profile_id=profile.id).first()
    if item is None:
        raise ApiError(404, "FAVORITE_NOT_FOUND", "Favorite meal not found.")
    return response(item)


@router.delete("/{favorite_id}", status_code=204)
def delete_favorite(favorite_id: UUID, db: Session = Depends(get_db)):
    profile = current_profile(db)
    item = db.query(FavoriteMeal).filter_by(id=favorite_id, profile_id=profile.id).first()
    if item is None:
        raise ApiError(404, "FAVORITE_NOT_FOUND", "Favorite meal not found.")
    db.delete(item)
    db.commit()
