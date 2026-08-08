import json
from typing import Literal, Protocol

from pydantic import BaseModel

from app.config import settings


ActivityType = Literal["walking", "hiking", "running", "cycling", "unknown"]


class ActivityInference(BaseModel):
    activity_type: ActivityType


class ActivityClassifier(Protocol):
    def classify(self, context: dict) -> ActivityType:
        ...


class FakeActivityClassifier:
    """Offline mode deliberately returns unknown so the UI correction flow is exercised."""

    def classify(self, context: dict) -> ActivityType:
        return "unknown"


class OpenAIActivityClassifier:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for live AI mode")
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.openai_api_key)

    def classify(self, context: dict) -> ActivityType:
        schema = {
            "type": "object",
            "properties": {
                "activity_type": {"type": "string", "enum": ["walking", "hiking", "running", "cycling", "unknown"]},
            },
            "required": ["activity_type"],
            "additionalProperties": False,
        }
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_schema", "json_schema": {"name": "activity_inference", "strict": True, "schema": schema}},
            messages=[
                {
                    "role": "system",
                    "content": "Classify the GPX activity using only the supplied metadata. Choose cycling, running, walking, hiking, or unknown. If evidence is insufficient or conflicting, choose unknown. Do not infer from unsupported sports.",
                },
                {"role": "user", "content": json.dumps(context)},
            ],
        )
        result = ActivityInference.model_validate_json(response.choices[0].message.content or '{"activity_type":"unknown"}')
        return result.activity_type


def get_activity_classifier() -> ActivityClassifier:
    if settings.ai_mode.casefold() == "live":
        try:
            return OpenAIActivityClassifier()
        except Exception:
            return FakeActivityClassifier()
    return FakeActivityClassifier()

