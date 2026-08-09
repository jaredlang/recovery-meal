from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.models import UserProfile
from app.schemas.account import AccountResponse, AccountUpdate
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.media import media_root, media_url, remove_media

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


def account_response(profile: UserProfile) -> AccountResponse:
    return AccountResponse(
        display_name=profile.display_name or "Athlete",
        email=profile.email,
        timezone=profile.timezone or "UTC",
        avatar_url=media_url(profile.avatar_filename),
    )


@router.get("/account", response_model=AccountResponse)
def get_account(db: Session = Depends(get_db)):
    return account_response(current_profile(db))


@router.put("/account", response_model=AccountResponse)
def put_account(payload: AccountUpdate, db: Session = Depends(get_db)):
    profile = current_profile(db)
    profile.display_name = payload.display_name
    profile.email = payload.email
    profile.timezone = payload.timezone
    db.commit()
    db.refresh(profile)
    return account_response(profile)


@router.post("/account/avatar", response_model=AccountResponse)
async def upload_avatar(file: UploadFile = File(...), db: Session = Depends(get_db)):
    profile = current_profile(db)
    content_type = (file.content_type or "").lower()
    extensions = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    if content_type not in extensions:
        raise ApiError(400, "INVALID_AVATAR", "Avatar must be a PNG, JPEG, or WebP image.")
    content = await file.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise ApiError(400, "AVATAR_TOO_LARGE", "Avatar must be no larger than 2 MB.")
    filename = f"avatar-{uuid4().hex}{extensions[content_type]}"
    (media_root() / filename).write_bytes(content)
    remove_media(profile.avatar_filename)
    profile.avatar_filename = filename
    db.commit()
    db.refresh(profile)
    return account_response(profile)


@router.delete("/account", status_code=204)
def delete_account(db: Session = Depends(get_db)):
    profile = current_profile(db)
    filenames = [profile.avatar_filename]
    filenames.extend(meal.image_filename for workout in profile.workouts for meal in workout.recommendations)
    filenames.extend(favorite.image_filename for favorite in profile.favorites)
    db.delete(profile)
    db.commit()
    for filename in set(filter(None, filenames)):
        remove_media(filename)

