import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(20))
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    fitness_goal: Mapped[str] = mapped_column(String(40))
    foods_to_avoid: Mapped[list] = mapped_column(JSON, default=list)
    favorite_foods: Mapped[list] = mapped_column(JSON, default=list)
    max_prep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_preference: Mapped[str] = mapped_column(String(20), default="metric")
    display_name: Mapped[str] = mapped_column(String(120), default="Athlete")
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    timezone: Mapped[str] = mapped_column(String(80), default="UTC")
    avatar_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    inventory: Mapped[list["InventoryItem"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    workouts: Mapped[list["Workout"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    favorites: Mapped[list["FavoriteMeal"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class InventoryItem(Base):
    __tablename__ = "inventory_item"
    __table_args__ = (UniqueConstraint("profile_id", "normalized_name", name="uq_inventory_profile_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_profile.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    profile: Mapped[UserProfile] = relationship(back_populates="inventory")


class Workout(Base):
    __tablename__ = "workout"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_profile.id", ondelete="CASCADE"))
    activity_type: Mapped[str] = mapped_column(String(40), default="unknown")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    moving_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    pre_exercise_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_exercise_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    met_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    intensity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estimated_calories_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_calories_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    profile: Mapped[UserProfile] = relationship(back_populates="workouts")
    recovery_target: Mapped["RecoveryTarget | None"] = relationship(back_populates="workout", uselist=False, cascade="all, delete-orphan")
    recommendations: Mapped[list["MealRecommendation"]] = relationship(back_populates="workout", cascade="all, delete-orphan")


class RecoveryTarget(Base):
    __tablename__ = "recovery_target"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workout.id", ondelete="CASCADE"), unique=True)
    protein_g_low: Mapped[int] = mapped_column(Integer)
    protein_g_high: Mapped[int] = mapped_column(Integer)
    carbs_g_low: Mapped[int] = mapped_column(Integer)
    carbs_g_high: Mapped[int] = mapped_column(Integer)
    fluid_ml_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fluid_ml_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calculation_version: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    workout: Mapped[Workout] = relationship(back_populates="recovery_target")


class MealRecommendation(Base):
    __tablename__ = "meal_recommendation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workout.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(180))
    ingredients: Mapped[list] = mapped_column(JSON)
    preparation_steps: Mapped[list] = mapped_column(JSON)
    prep_minutes: Mapped[int] = mapped_column(Integer)
    estimated_calories: Mapped[int] = mapped_column(Integer)
    protein_g: Mapped[int] = mapped_column(Integer)
    carbs_g: Mapped[int] = mapped_column(Integer)
    fat_g: Mapped[int] = mapped_column(Integer)
    rationale: Mapped[str] = mapped_column(String(2000))
    missing_ingredients: Mapped[list] = mapped_column(JSON, default=list)
    recovery_match_score: Mapped[float] = mapped_column(Float)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    image_status: Mapped[str] = mapped_column(String(20), default="pending")
    image_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    workout: Mapped[Workout] = relationship(back_populates="recommendations")


class FavoriteMeal(Base):
    __tablename__ = "favorite_meal"
    __table_args__ = (UniqueConstraint("profile_id", "recommendation_id", name="uq_favorite_profile_recommendation"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_profile.id", ondelete="CASCADE"))
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("meal_recommendation.id", ondelete="SET NULL"), nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    image_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    profile: Mapped[UserProfile] = relationship(back_populates="favorites")

