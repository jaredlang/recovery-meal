from dataclasses import dataclass
import unicodedata

from app.ai.food_matcher import FoodMatcher, get_food_matcher


@dataclass(frozen=True)
class FoodMatchTable:
    matches: dict[str, set[str]]

    def has_match(self, candidate: str) -> bool:
        return bool(self.matches.get(normalize_food(candidate), set()))


def normalize_food(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().strip().split())


def match_foods(candidates: list[str], references: list[str], matcher: FoodMatcher | None = None) -> FoodMatchTable:
    """Ask the configured AI matcher to compare two closed lists in one batch."""
    if not candidates or not references:
        return FoodMatchTable({normalize_food(candidate): set() for candidate in candidates})
    engine = matcher or get_food_matcher()
    raw_matches = engine.match(candidates, references)
    allowed = {normalize_food(reference): reference for reference in references}
    sanitized: dict[str, set[str]] = {}
    for candidate in candidates:
        supplied = raw_matches.get(candidate, set())
        sanitized[normalize_food(candidate)] = {allowed[normalize_food(reference)] for reference in supplied if normalize_food(reference) in allowed}
    return FoodMatchTable(sanitized)


def foods_match(left: str, right: str, matcher: FoodMatcher | None = None) -> bool:
    """Compatibility helper; callers doing multiple comparisons should use match_foods."""
    return match_foods([left], [right], matcher).has_match(left)

