from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MealIngredient(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=30)
    available: bool = False


class MealCandidate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    ingredients: list[MealIngredient] = Field(min_length=1, max_length=30)
    preparation_steps: list[str] = Field(min_length=1, max_length=20)
    prep_minutes: int = Field(gt=0, le=120)
    protein_g: int = Field(ge=0, le=300)
    carbs_g: int = Field(ge=0, le=500)
    fat_g: int = Field(ge=0, le=300)
    rationale: str = Field(min_length=1, max_length=2000)


class MealResponse(BaseModel):
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
    missing_ingredients: list[str]
    recovery_match_score: float
    selected: bool
    selected_at: datetime | None = None
    image_status: str = "pending"
    image_url: str | None = None
    favorite: bool = False


class RecommendationsResponse(BaseModel):
    recommendations: list[MealResponse]


class FavoriteResponse(BaseModel):
    id: UUID
    recommendation_id: UUID | None
    meal: dict
    image_url: str | None
    created_at: datetime

