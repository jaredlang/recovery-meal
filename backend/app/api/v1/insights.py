import calendar
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.profile import account_response, current_profile
from app.api.v1.workouts import meal_response, workout_response
from app.db.session import get_db
from app.models import FavoriteMeal, MealRecommendation, Workout

router = APIRouter(tags=["insights"])


def local_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def localized(value: datetime, zone: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(zone)


def workout_day(workout: Workout, zone: ZoneInfo) -> date:
    return localized(workout.started_at or workout.created_at, zone).date()


def selected_by_day(profile_id, db: Session, zone: ZoneInfo) -> dict[date, MealRecommendation]:
    meals = (
        db.query(MealRecommendation)
        .join(Workout)
        .filter(Workout.profile_id == profile_id, MealRecommendation.selected.is_(True))
        .all()
    )
    return {workout_day(meal.workout, zone): meal for meal in meals}


def current_streak(selected_days: set[date], today: date) -> int:
    cursor = today if today in selected_days else today - timedelta(days=1)
    streak = 0
    while cursor in selected_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    profile = current_profile(db)
    zone = local_zone(profile.timezone)
    today = datetime.now(zone).date()
    workouts = db.query(Workout).filter_by(profile_id=profile.id).order_by(Workout.created_at.desc()).all()
    latest_workout = workouts[0] if workouts else None
    latest_meal = (
        db.query(MealRecommendation)
        .join(Workout)
        .filter(Workout.profile_id == profile.id, MealRecommendation.selected.is_(True))
        .order_by(MealRecommendation.selected_at.desc())
        .first()
    )
    selected = selected_by_day(profile.id, db, zone)
    monday = today - timedelta(days=today.weekday())
    week_days = [monday + timedelta(days=index) for index in range(7)]
    week_count = sum(day in selected for day in week_days)
    activity: list[dict] = []
    for workout in workouts[:8]:
        activity.append({
            "type": "workout", "at": workout.created_at, "title": f"Completed {workout.activity_type.title()}",
            "detail": f"{round((workout.duration_seconds or 0) / 60)} min",
        })
    selected_meals = (
        db.query(MealRecommendation)
        .join(Workout)
        .filter(Workout.profile_id == profile.id, MealRecommendation.selected.is_(True))
        .all()
    )
    for meal in selected_meals:
        activity.append({"type": "meal", "at": meal.selected_at, "title": f"Logged {meal.name}", "detail": f"{meal.estimated_calories} kcal · {meal.protein_g}g protein"})
    for favorite in db.query(FavoriteMeal).filter_by(profile_id=profile.id).all():
        activity.append({"type": "favorite", "at": favorite.created_at, "title": "Added to favorites", "detail": favorite.snapshot.get("name", "Meal")})
    activity.sort(key=lambda item: item["at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return {
        "account": account_response(profile).model_dump(),
        "latest_workout": workout_response(latest_workout).model_dump() if latest_workout else None,
        "latest_meal": meal_response(latest_meal, db).model_dump() if latest_meal else None,
        "streak": current_streak(set(selected), today),
        "week": {
            "selected": week_count, "goal": 7, "percent": round(week_count / 7 * 100),
            "days": [{"date": day.isoformat(), "selected": day in selected, "today": day == today} for day in week_days],
        },
        "recent_activity": activity[:6],
    }


@router.get("/progress")
def progress(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db)):
    profile = current_profile(db)
    try:
        year, month_number = (int(part) for part in month.split("-"))
        first = date(year, month_number, 1)
    except (ValueError, TypeError) as exc:
        raise ApiError(422, "INVALID_MONTH", "Month must be a valid YYYY-MM value.") from exc
    zone = local_zone(profile.timezone)
    today = datetime.now(zone).date()
    selected = selected_by_day(profile.id, db, zone)
    workouts = db.query(Workout).filter_by(profile_id=profile.id).all()
    by_day = {workout_day(item, zone): item for item in workouts}
    _, days_in_month = calendar.monthrange(year, month_number)
    days = []
    for day_number in range(1, days_in_month + 1):
        day = date(year, month_number, day_number)
        workout = by_day.get(day)
        meal = selected.get(day)
        days.append({
            "date": day.isoformat(), "is_today": day == today, "is_future": day > today,
            "workout": workout_response(workout).model_dump() if workout else None,
            "meal": meal_response(meal, db).model_dump() if meal else None,
        })
    return {"month": first.strftime("%Y-%m"), "streak": current_streak(set(selected), today), "days": days}
