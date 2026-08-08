from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.models import UserProfile
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


def current_profile(db: Session) -> UserProfile:
    profile = db.query(UserProfile).first()
    if not profile:
        raise ApiError(404, "PROFILE_REQUIRED", "Create a profile before using the application.")
    return profile


@router.get("", response_model=ProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    return current_profile(db)


@router.put("", response_model=ProfileResponse)
def put_profile(payload: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).first()
    if profile is None:
        profile = UserProfile(**payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile

