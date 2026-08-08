import json
from typing import Protocol

from app.config import settings
from app.schemas.recommendation import MealCandidate, MealIngredient


class MealGenerator(Protocol):
    def generate(self, context: dict) -> list[MealCandidate]:
        ...


class FakeMealGenerator:
    def generate(self, context: dict) -> list[MealCandidate]:
        foods = context["available_foods"]
        first = foods[0] if foods else "chicken"
        second = foods[1] if len(foods) > 1 else "rice"
        third = foods[2] if len(foods) > 2 else "banana"
        return [
            MealCandidate(
                name=f"{first.title()} and {second.title()} Recovery Bowl",
                ingredients=[
                    MealIngredient(name=first, quantity=150, unit="g"),
                    MealIngredient(name=second, quantity=250, unit="g"),
                    MealIngredient(name=third, quantity=1, unit="medium"),
                ],
                preparation_steps=[f"Prepare the {first}.", f"Warm or cook the {second}.", f"Serve with the {third}."],
                prep_minutes=min(context["max_prep_minutes"] or 20, 20),
                protein_g=32,
                carbs_g=85,
                fat_g=16,
                rationale="A deterministic local-mode candidate combining protein and carbohydrate sources for post-workout recovery.",
            ),
            MealCandidate(
                name=f"Quick {third.title()} Protein Plate",
                ingredients=[
                    MealIngredient(name=third, quantity=1, unit="medium"),
                    MealIngredient(name=first, quantity=120, unit="g"),
                ],
                preparation_steps=[f"Prepare the {first}.", f"Serve with the {third}."],
                prep_minutes=10,
                protein_g=28,
                carbs_g=55,
                fat_g=12,
                rationale="A fast local-mode option with a compact protein and carbohydrate combination.",
            ),
            MealCandidate(
                name="Simple Oat Recovery Bowl",
                ingredients=[
                    MealIngredient(name="oats", quantity=80, unit="g"),
                    MealIngredient(name="milk", quantity=250, unit="ml"),
                    MealIngredient(name=third, quantity=1, unit="medium"),
                ],
                preparation_steps=["Combine the oats and milk.", "Heat until soft.", "Top with fruit."],
                prep_minutes=8,
                protein_g=24,
                carbs_g=78,
                fat_g=10,
                rationale="A quick carbohydrate-forward option with moderate protein for recovery.",
            ),
        ]


class OpenAIMealGenerator:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for live AI mode")
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate(self, context: dict) -> list[MealCandidate]:
        ingredient_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}, "quantity": {"type": "number"}, "unit": {"type": "string"}, "available": {"type": "boolean"},
            },
            "required": ["name", "quantity", "unit", "available"], "additionalProperties": False,
        }
        meal_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}, "ingredients": {"type": "array", "items": ingredient_schema},
                "preparation_steps": {"type": "array", "items": {"type": "string"}}, "prep_minutes": {"type": "integer"},
                "protein_g": {"type": "integer"}, "carbs_g": {"type": "integer"}, "fat_g": {"type": "integer"}, "rationale": {"type": "string"},
            },
            "required": ["name", "ingredients", "preparation_steps", "prep_minutes", "protein_g", "carbs_g", "fat_g", "rationale"],
            "additionalProperties": False,
        }
        schema = {
            "type": "object",
            "properties": {
                "meals": {"type": "array", "maxItems": 6, "items": meal_schema},
            },
            "required": ["meals"],
            "additionalProperties": False,
        }
        instructions = (
            "Return only JSON matching the schema. Generate practical post-workout meals. "
            "Use the recovery target exactly as supplied. Every ingredient needs name, quantity, unit, and available. "
            "Only mark an ingredient available if it matches available_foods. Do not use foods_to_avoid. "
            "Return up to six differentiated candidates."
        )
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_schema", "json_schema": {"name": "meal_candidates", "strict": False, "schema": schema}},
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(context)},
            ],
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        return [MealCandidate.model_validate(item) for item in raw.get("meals", [])]


def get_meal_generator() -> MealGenerator:
    return OpenAIMealGenerator() if settings.ai_mode.casefold() == "live" else FakeMealGenerator()
