from datetime import date

import pytest
from pydantic import ValidationError

from app.ai.meal_image import MealImageGenerator, meal_image_prompt
from app.api.v1.insights import current_streak
from app.schemas.account import AccountUpdate


def test_current_streak_counts_today_or_yesterday_anchor():
    today = date(2026, 8, 9)
    assert current_streak({date(2026, 8, 7), date(2026, 8, 8)}, today) == 2
    assert current_streak({date(2026, 8, 7), date(2026, 8, 8), today}, today) == 3
    assert current_streak({date(2026, 8, 6)}, today) == 0


def test_meal_image_prompt_uses_recipe_without_branding():
    prompt = meal_image_prompt("Chicken Rice Bowl", [{"name": "chicken"}, {"name": "rice"}])
    assert "Chicken Rice Bowl" in prompt
    assert "chicken, rice" in prompt
    assert "No text" in prompt


def test_fake_meal_image_generation_is_local_and_deterministic(monkeypatch):
    monkeypatch.setattr("app.ai.meal_image.settings.image_mode", "fake")
    result = MealImageGenerator().generate("Oat Bowl", [{"name": "oats"}])
    assert result.extension == ".svg"
    assert result.data.startswith(b"<svg")


def test_account_normalizes_identity_and_validates_timezone():
    account = AccountUpdate(display_name="  Alex   Morgan ", email=" alex@example.com ", timezone="UTC")
    assert account.display_name == "Alex Morgan"
    assert account.email == "alex@example.com"
    with pytest.raises(ValidationError):
        AccountUpdate(display_name="Alex", email="alex@example.com", timezone="Not/AZone")
