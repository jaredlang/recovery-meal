from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def clean_list(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(value.strip().split())
        key = cleaned.casefold()
        if cleaned and key not in seen:
            output.append(cleaned)
            seen.add(key)
    return output


class ProfileUpdate(BaseModel):
    age: int = Field(ge=13, le=100)
    sex: Literal["male", "female", "other", "prefer_not_to_say"]
    height_cm: float = Field(gt=0, le=300)
    weight_kg: float = Field(gt=0, le=500)
    fitness_goal: Literal["maintain_weight", "lose_weight", "gain_muscle", "endurance_performance"]
    foods_to_avoid: list[str] = Field(default_factory=list, max_length=100)
    favorite_foods: list[str] = Field(default_factory=list, max_length=100)
    max_prep_minutes: int | None = Field(default=None, ge=1, le=120)
    unit_preference: Literal["metric", "imperial"] = "metric"

    @field_validator("foods_to_avoid", "favorite_foods")
    @classmethod
    def normalize_lists(cls, values: list[str]) -> list[str]:
        return clean_list(values)


class ProfileResponse(ProfileUpdate):
    id: UUID

    model_config = {"from_attributes": True}

