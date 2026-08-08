# Recovery Meal Recommendation — Developer Design V1

Status: Implemented MVP design

## 1. Objective and scope

The application converts a completed GPX workout into up to three practical post-workout meals. It is general fitness and nutrition guidance, not medical advice.

V1 includes one persisted user profile, available-food inventory, GPX ingestion, AI activity inference, manual workout correction, deterministic workout/recovery calculations, AI meal generation, AI food matching, meal selection, and local Docker Compose development.

V1 excludes dietary restrictions, authentication, multi-user authorization, wearables, restaurant/grocery integrations, nutrition databases, recommendation history, object storage, queues, microservices, RAG, and vector databases. `foods_to_avoid` remains active as a hard exclusion; dietary restrictions are not part of the V1 contract or UI.

## 2. Architecture

```text
React + TypeScript UI
        | REST /api/v1
        v
FastAPI modular monolith
  |-- SQLAlchemy + Alembic --> PostgreSQL
  |-- deterministic calculation services
  |     GPX metrics, MET, intensity, energy, recovery
  |-- AI adapters
        ActivityClassifier, FoodMatcher, MealGenerator
```

The frontend owns display state and unit conversion only. Business rules, validation, ranking, AI calls, and persistence remain in the backend.

Repository structure:

```text
frontend/src/                 React UI, REST client, types, styles
backend/app/api/v1/           FastAPI routes
backend/app/ai/               AI protocols and adapters
backend/app/calculations/     Versioned deterministic formulas
backend/app/models/           SQLAlchemy models
backend/app/schemas/          Pydantic contracts
backend/app/services/         Domain orchestration
backend/migrations/           Alembic migrations
backend/tests/                Backend unit tests
```

## 3. Domain boundaries

| Component | Owns | Must not own |
| --- | --- | --- |
| `WorkoutService` | GPX parsing, metrics, activity-classifier delegation | Meal generation |
| `calculations/*` | MET, intensity, energy, recovery formulas | Network/AI calls |
| `RecommendationService` | Context, matching, validation, ranking, persistence preparation | GPX/calculation logic |
| `ActivityClassifier` | Activity label from GPX context | Workout metrics |
| `FoodMatcher` | Semantic comparison of closed food lists | Inventing food names |
| `MealGenerator` | Structured meal candidates and rationale | Overriding hard constraints |

Each AI capability is behind a protocol and can be replaced by a deterministic test double.

## 4. End-to-end workflow

```text
Profile -> inventory -> GPX upload -> AI activity inference
       -> review/correct activity and duration -> calculate workout fields
       -> calculate recovery target -> build RecoveryContext
       -> generate candidates -> batch AI food matching
       -> validate hard constraints -> rank/categorize -> replace saved meals
       -> display meals -> persist one selected meal
```

### Local AI modes

- `AI_MODE=fake` is the default. Meal generation is deterministic, activity inference returns `unknown`, and food matching uses exact normalized names. This makes local tests independent of model calls.
- `AI_MODE=live` uses `OPENAI_API_KEY` and `OPENAI_MODEL` for activity inference, food matching, and meal generation.

## 5. Profile contract

There is exactly one profile in V1. `PUT /api/v1/profile` creates it if absent and replaces its values if present.

| Field | Type/rules |
| --- | --- |
| `age` | integer, 13–100 |
| `sex` | `male`, `female`, `other`, `prefer_not_to_say` |
| `height_cm` | positive canonical metric value |
| `weight_kg` | positive canonical metric value |
| `fitness_goal` | `maintain_weight`, `lose_weight`, `gain_muscle`, `endurance_performance` |
| `foods_to_avoid` | trimmed, case-insensitive de-duplicated string list |
| `favorite_foods` | trimmed, case-insensitive de-duplicated string list |
| `max_prep_minutes` | integer 1–120, or null for no preference |
| `unit_preference` | `metric` or `imperial` |

The UI accepts metric or imperial height/weight, converts to metric before submission, and stores the preference for display.

## 6. GPX and workout design

`POST /api/v1/workouts` accepts a multipart GPX upload up to 10 MB. Content is parsed and validated; the extension is not trusted. Invalid GPX, empty tracks, and oversized files do not create a workout.

The parser calculates:

- duration from usable point timestamps;
- distance from consecutive coordinates;
- positive elevation gain when elevation exists;
- average/max heart rate from recognized GPX HR extensions;
- average speed when distance and duration are available.

`moving_seconds` initially equals derived duration. No pause-gap heuristic is used. If no usable start timestamp exists, `started_at` uses server upload time in UTC. If duration cannot be derived, the workout is persisted for correction but cannot proceed to recovery calculation.

### AI activity inference

Activity inference is not performed with filename or word-pattern matching. `ActivityClassifier` receives GPX creator/name/description, extension text, and filename and returns exactly one of:

```text
cycling | running | walking | hiking | unknown
```

The live adapter uses temperature-zero structured JSON output. Insufficient/conflicting evidence, adapter failure, or missing credentials results in `unknown`.

### Correction endpoint

```http
PATCH /api/v1/workouts/{workoutId}/correction
Content-Type: application/json
```

```json
{"activity_type": "cycling", "duration_seconds": 5400}
```

The correction updates both `duration_seconds` and `moving_seconds`, recalculates average speed, MET, intensity, and energy range. The UI blocks recovery calculation until a supported activity and duration are saved.
## 7. Deterministic calculation design

Calculation version: `v1.1`. Formula code is under `backend/app/calculations/`; it makes no network calls.

### MET

Activity-specific MET is selected from average moving speed using the documented 2024 Adult Compendium lookup:

- cycling: 4.0, 6.8, 8.0, 10.0, 12.0, or 16.8 MET;
- running: 3.3 through 16.8 MET by speed band;
- walking: 2.3 through 8.5 MET by speed band;
- hiking: 5.3 MET, or 3.8 MET below 2 mph.

Elevation does not alter MET in V1.

### Intensity

Valid average HR takes precedence:

```text
predicted_hr_max = 208 - (0.7 * age)
fraction = avg_heart_rate / predicted_hr_max
low < 0.64; moderate < 0.77; high >= 0.77
```

Without valid HR: low is `MET < 3.0`, moderate is `3.0 <= MET <= 6.0`, and high is `MET > 6.0`.

### Net exercise energy

```text
mid = max(MET - 1.0, 0) * 3.5 * weight_kg / 200 * moving_minutes
low = round(mid * 0.80)
high = round(mid * 1.20)
```

### Recovery target

V1 does not calculate a recovery-calorie replacement target. Meal calories are derived from meal macros only.

```text
protein_low  = clamp(weight_kg * 0.25, 20, 40)
protein_high = clamp(weight_kg * 0.40, 20, 40)
```

Carbohydrate factors are `0.40/0.60` for low intensity, `0.60/0.80` for moderate, and `0.80/1.00` for high. Moderate/high workouts lasting at least 90 minutes use `1.00/1.20`. All values are rounded to integers.

Numeric fluid replacement exists only when both body weights are provided:

```text
loss = max(pre_weight_kg - post_weight_kg, 0)
fluid_low = round(loss * 1000 * 1.25)
fluid_high = round(loss * 1000 * 1.50)
```

Otherwise fluid is null.

## 8. AI integration contracts

### ActivityClassifier

```python
class ActivityClassifier(Protocol):
    def classify(self, context: dict) -> ActivityType: ...
```

The output schema is `{ "activity_type": "cycling" }` with a closed enum.

### FoodMatcher

Food matching is batch-oriented, not one model request per pair. For each candidate set, all unique ingredient names are compared against:

1. available inventory;
2. foods to avoid;
3. favorite foods.

The live AI receives closed candidate/reference lists. It may identify semantic equivalence such as `chicken`/`chicken breast` or `steak`/`rib eye`, but may return only reference values present in the request. The backend sanitizes the response and derives `available`, `missing_ingredients`, and favorite matches itself.

### MealGenerator

The generator receives profile facts, workout summary, protein/carbohydrate targets, avoid list, favorite foods, available inventory, and maximum prep time. It returns candidates with:

- name;
- ingredients `{name, quantity, unit, available}`;
- ordered preparation steps;
- `prep_minutes`;
- `protein_g`, `carbs_g`, `fat_g`;
- rationale.

The application ignores AI calories and derives:

```text
estimated_calories = round(4*protein_g + 4*carbs_g + 9*fat_g)
```

## 9. Recommendation validation/ranking

Candidates are rejected when they fail schema validation, exceed `max_prep_minutes`, or contain an ingredient matched to `foods_to_avoid`. AI availability flags are never trusted.

If every candidate is rejected, one bounded correction retry is made. A second failure returns an empty result and creates no partial rows.

The score combines protein/carbohydrate target distance, inventory coverage, prep fit, favorite-food preference, and a small lower-fat preference for weight loss. Up to three distinct cards are selected from:

- `best_recovery_match`;
- `fastest`;
- `best_use_of_inventory`.

Re-running generation deletes prior recommendations for that workout and inserts the new set transactionally. Selection clears all other selections for the same workout.

## 10. Persistence model

### `user_profile`

UUID, physical profile, fitness goal, `foods_to_avoid`, `favorite_foods`, `max_prep_minutes`, `unit_preference`, and timestamps.

### `inventory_item`

UUID, profile FK, display name, normalized name, and timestamp. `(profile_id, normalized_name)` is unique.

### `workout`

UUID, profile FK, activity, start time, duration/moving seconds, distance, elevation, speed, HR fields, optional pre/post weights, MET, intensity, energy range, source filename, and timestamp.

### `recovery_target`

One row per workout containing rounded protein/carbohydrate ranges, optional fluid range, calculation version, and timestamp.

### `meal_recommendation`

Workout FK, category, name, JSON ingredients, JSON preparation steps, prep time, derived calories, macros, rationale, missing ingredients, score, selected flag, and timestamp.

## 11. API surface

Base path: `/api/v1`. UUID IDs and UTC ISO-8601 timestamps are used. Errors use:

```json
{"error":{"code":"CODE","message":"Human-readable message","details":null}}
```

```text
GET    /profile
PUT    /profile
GET    /inventory
POST   /inventory
DELETE /inventory/{itemId}
POST   /workouts
GET    /workouts/{workoutId}
PATCH  /workouts/{workoutId}/correction
POST   /workouts/{workoutId}/recovery-target
POST   /workouts/{workoutId}/recommendations
GET    /workouts/{workoutId}/recommendations
POST   /recommendations/{recommendationId}/select
```

Important expected errors:

| Condition | Status/code |
| --- | --- |
| Invalid request | 422 `VALIDATION_ERROR` |
| Invalid GPX | 400 `INVALID_GPX` |
| Missing profile/workout/recommendation | 404 resource-specific code |
| Duplicate inventory | 409 `DUPLICATE_INVENTORY_ITEM` |
| Incomplete workout | 422 `CALCULATION_INPUT_INCOMPLETE` |
| Missing recovery target | 422 `RECOVERY_TARGET_REQUIRED` |
| AI meal failure | 502 `MEAL_GENERATION_FAILED` |

## 12. Frontend screens

- **Profile:** physical fields, goal, metric/imperial preference, max prep time, favorites, foods to avoid.
- **Available food:** add, list, and delete inventory items.
- **Upload workout:** GPX file selection and upload errors.
- **Workout review:** parsed metrics, inferred activity, editable activity/duration, optional pre/post weights, recovery action.
- **Recommendations:** integer recovery ranges, generate action, up to three cards, ingredients with quantities/units, missing-item labels, instructions, estimated nutrition, rationale, and selection.

The UI does not call AI directly or implement business calculations.

## 13. Local development

```sh
cp .env.example .env
docker compose up --build
```

Services:

- frontend: `http://localhost:5173`;
- backend API: `http://localhost:8000`;
- Swagger: `http://localhost:8000/docs`;
- PostgreSQL: `localhost:5432`.

The backend container runs `alembic upgrade head` before Uvicorn. A hosted PostgreSQL service such as Supabase can be used by changing `DATABASE_URL`.

## 14. Verification requirements

Unit tests must cover MET boundaries, HR precedence, energy scaling, rounded recovery targets, fluid null/measured branches, GPX optional fields, AI adapter fallbacks, food-match sanitization, hard constraints, ranking, and selection replacement.

Integration tests should run the full profile → inventory → GPX → correction → recovery → recommendation → selection workflow with fake adapters. Live AI is reserved for a manual schema-compatibility smoke test.

The CI gate is backend formatting/linting/tests, frontend typecheck/build/tests, and applying migrations to an empty PostgreSQL database.

## 15. Future extension points

- Add authentication and profile ownership.
- Retain recommendation generations and selections as historical data.
- Replace or supplement AI food matching with a verified nutrition taxonomy if reliability requires it.
- Add raw GPX object storage.
- Add activity-correction history and user preference learning.
- Add nutrition database validation.
