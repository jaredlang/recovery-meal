import base64
from dataclasses import dataclass

from app.config import settings


@dataclass
class GeneratedImage:
    data: bytes
    extension: str


def meal_image_prompt(name: str, ingredients: list[dict]) -> str:
    ingredient_names = ", ".join(str(item.get("name", "")) for item in ingredients[:10])
    return (
        "Use case: photorealistic-natural. Asset type: recovery meal recipe card. "
        f"Create an appetizing editorial food photograph of {name}, visibly featuring {ingredient_names}. "
        "Three-quarter overhead composition in a simple ceramic bowl or plate, soft natural daylight, "
        "light neutral tabletop, realistic texture, restrained green garnish, generous crop-safe margins. "
        "No text, labels, logos, packages, people, hands, utensils blocking the food, or watermark."
    )


class MealImageGenerator:
    def generate(self, name: str, ingredients: list[dict]) -> GeneratedImage:
        if settings.image_mode.casefold() != "live":
            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f1f6ed"/><stop offset="1" stop-color="#dcebd8"/></linearGradient></defs>
<rect width="1024" height="1024" fill="url(#g)"/><ellipse cx="512" cy="555" rx="330" ry="250" fill="#fff" stroke="#c6d6c3" stroke-width="28"/>
<ellipse cx="512" cy="530" rx="275" ry="195" fill="#e7b96b"/><circle cx="420" cy="480" r="78" fill="#4f8b3c"/><circle cx="610" cy="470" r="90" fill="#d77a42"/>
<path d="M350 620c95-100 230-110 330 0" fill="none" stroke="#f5e9c8" stroke-width="90" stroke-linecap="round"/></svg>'''
            return GeneratedImage(svg.encode("utf-8"), ".svg")
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for live image mode")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        result = client.images.generate(
            model=settings.openai_image_model,
            prompt=meal_image_prompt(name, ingredients),
            size="1024x1024",
            quality="medium",
        )
        encoded = result.data[0].b64_json
        if not encoded:
            raise RuntimeError("Image generation returned no image data")
        return GeneratedImage(base64.b64decode(encoded), ".png")


def get_meal_image_generator() -> MealImageGenerator:
    return MealImageGenerator()
