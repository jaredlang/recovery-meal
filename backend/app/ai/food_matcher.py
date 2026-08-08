import json
from typing import Protocol

from pydantic import BaseModel, Field

from app.config import settings


class FoodMatch(BaseModel):
    candidate: str = Field(min_length=1)
    matches: list[str] = Field(default_factory=list)


class FoodMatchResult(BaseModel):
    matches: list[FoodMatch] = Field(default_factory=list)


class FoodMatcher(Protocol):
    def match(self, candidates: list[str], references: list[str]) -> dict[str, set[str]]:
        """Return candidate -> semantically matching supplied reference names."""
        ...


class FakeFoodMatcher:
    """Offline matcher used by fake mode; it only proves exact-name plumbing."""

    def match(self, candidates: list[str], references: list[str]) -> dict[str, set[str]]:
        reference_by_key = {value.casefold().strip(): value for value in references}
        return {
            candidate: {reference_by_key[candidate.casefold().strip()]}
            if candidate.casefold().strip() in reference_by_key else set()
            for candidate in candidates
        }


class OpenAIFoodMatcher:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for live AI mode")
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.openai_api_key)

    def match(self, candidates: list[str], references: list[str]) -> dict[str, set[str]]:
        if not candidates or not references:
            return {candidate: set() for candidate in candidates}
        schema = {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "candidate": {"type": "string"},
                            "matches": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["candidate", "matches"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["matches"],
            "additionalProperties": False,
        }
        prompt = {
            "candidates": candidates,
            "references": references,
            "task": "Match foods by ordinary food category or equivalent ingredient. Chicken matches chicken breast and chicken legs. Steak matches rib eye and t-bone. Return only reference values supplied in the references list; do not invent values.",
        }
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_schema", "json_schema": {"name": "food_matches", "strict": True, "schema": schema}},
            messages=[
                {"role": "system", "content": "You are a conservative food equivalence matcher. Treat the supplied lists as closed sets."},
                {"role": "user", "content": json.dumps(prompt)},
            ],
        )
        parsed = FoodMatchResult.model_validate_json(response.choices[0].message.content or '{"matches": []}')
        allowed_candidates = {candidate.casefold().strip(): candidate for candidate in candidates}
        allowed_references = {reference.casefold().strip(): reference for reference in references}
        result = {candidate: set() for candidate in candidates}
        for item in parsed.matches:
            candidate = allowed_candidates.get(item.candidate.casefold().strip())
            if candidate is None:
                continue
            for reference in item.matches:
                supplied_reference = allowed_references.get(reference.casefold().strip())
                if supplied_reference is not None:
                    result[candidate].add(supplied_reference)
        return result


def get_food_matcher() -> FoodMatcher:
    return OpenAIFoodMatcher() if settings.ai_mode.casefold() == "live" else FakeFoodMatcher()

