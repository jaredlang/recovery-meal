from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


ActivityType = Literal["walking", "hiking", "running", "cycling", "unknown"]


class WorkoutCorrection(BaseModel):
    activity_type: ActivityType
    duration_seconds: int = Field(gt=0, le=172800)


class WeightInput(BaseModel):
    pre_exercise_weight_kg: float | None = Field(default=None, gt=0, le=500)
    post_exercise_weight_kg: float | None = Field(default=None, gt=0, le=500)


class RangeResponse(BaseModel):
    low: int
    high: int


class WorkoutResponse(BaseModel):
    id: UUID
    activity_type: str
    started_at: datetime | None
    duration_seconds: int | None
    moving_seconds: int | None
    distance_meters: float | None
    elevation_gain_meters: float | None
    avg_speed_mps: float | None
    avg_heart_rate: float | None
    max_heart_rate: float | None
    intensity: str | None
    met_value: float | None
    estimated_calories: RangeResponse | None
    source_filename: str


class RecoveryResponse(BaseModel):
    workout_id: UUID
    protein_g: RangeResponse
    carbs_g: RangeResponse
    fluid_ml: RangeResponse | None
    calculation_version: str

