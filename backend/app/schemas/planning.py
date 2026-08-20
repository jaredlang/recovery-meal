from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.recommendation import MealIngredient
from app.schemas.workout import RangeResponse


ExpectedIntensity = Literal["low", "moderate", "high"]


class PlannedWorkoutCreate(BaseModel):
    scheduled_for: date
    display_activity: str = Field(min_length=1, max_length=120)
    duration_minutes: int = Field(gt=0, le=2880)
    expected_intensity: ExpectedIntensity


class PlannedWorkoutUpdate(PlannedWorkoutCreate):
    pass


class PlannedRecoveryTarget(BaseModel):
    protein_g: RangeResponse
    carbs_g: RangeResponse


class PlannedMealResponse(BaseModel):
    id: UUID
    category: str
    name: str
    ingredients: list[MealIngredient]
    preparation_steps: list[str]
    prep_minutes: int
    estimated_calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    rationale: str
    recovery_match_score: float
    selected: bool
    selected_at: datetime | None


class PlannedWorkoutResponse(BaseModel):
    id: UUID
    scheduled_for: date
    activity_type: str
    display_activity: str
    normalized_activity: str
    duration_minutes: int
    expected_intensity: ExpectedIntensity
    recovery_target: PlannedRecoveryTarget | None
    needs_meal_selection: bool
    meal_options: list[PlannedMealResponse]


class GroceryLineResponse(BaseModel):
    id: UUID
    name: str
    quantity: float
    unit: str
    category: str
    available_at_home: bool
    checked: bool


class WeeklyPlanResponse(BaseModel):
    starts_on: date
    ends_on: date
    workouts: list[PlannedWorkoutResponse]
    grocery_lines: list[GroceryLineResponse]


class SubstitutionSuggestion(BaseModel):
    name: str
    reason: str


class SubstitutionSuggestionsResponse(BaseModel):
    ingredient_name: str
    suggestions: list[SubstitutionSuggestion]


class PlannedMealSubstitution(BaseModel):
    ingredient_name: str = Field(min_length=1, max_length=160)
    replacement_name: str = Field(min_length=1, max_length=160)


class GroceryLineCheck(BaseModel):
    checked: bool