# Recovery Meal Recommendation MVP

This local MVP turns a completed GPX workout into up to three practical recovery meals.

## Run locally

```sh
cp .env.example .env
docker compose up --build
```

Open the original frontend at [http://localhost:5173](http://localhost:5173), or the redesigned V2 experience at [http://localhost:5174](http://localhost:5174). Both use the same API and database.

`AI_MODE=fake` makes meal generation deterministic. Meal photography is separately controlled by `IMAGE_MODE`: keep it at `fake` for a deterministic local illustration, or set `IMAGE_MODE=live` with `OPENAI_API_KEY` to generate and persist a GPT Image 2 photograph for each recipe. `OPENAI_IMAGE_MODEL` defaults to `gpt-image-2`.

The API is available at [http://localhost:8000/docs](http://localhost:8000/docs). PostgreSQL runs locally in Docker. A hosted PostgreSQL provider such as Supabase can be used by changing `DATABASE_URL`.

## Workflow

1. Save the profile, including metric/imperial display preference and maximum preparation time.
2. Add available foods.
3. Upload a GPX file. Activity and duration are inferred where possible.
4. Correct activity or duration in the workout review screen when needed.
5. Optionally provide pre/post workout weights for a fluid target.
6. Calculate recovery, generate meals, and select one.

The backend uses deterministic calculations for distance, duration, intensity, exercise energy, and recovery targets. Activity type is inferred by the structured AI activity classifier; uncertain or unavailable inference becomes `unknown` and the UI asks the user to correct it. AI also handles meal synthesis, food matching, and explanation. Generated nutrition is labeled as estimated; calories are derived from the returned macros.

## Calculation notes

Calculation constants live under `backend/app/calculations/` and use version `v1.1`. The implementation uses the documented MET lookup, Tanaka HR estimate, net exercise energy range, rounded protein/carbohydrate targets, and measured-loss-only fluid range. A manual duration correction updates both elapsed and moving seconds for the calculation path.

Dietary restrictions are intentionally excluded from the active V1 contract and UI. Food equivalence is delegated to the AI food-matching adapter in live mode: it receives closed candidate/reference lists and may only return supplied reference values. Foods to avoid remain hard exclusions. Fake mode uses exact matching so local tests remain deterministic without model calls.

## Test commands

```sh
cd backend
pytest
cd ../frontend
npm install
npm run build
cd ../frontend-v2
npm install
npm test
npm run build
```

## Full-stack browser test

The dedicated Playwright suite drives Chromium through the V2 UI while using the real FastAPI service and a disposable PostgreSQL database. It runs on isolated ports (`5184` for the browser app and `8010` for the API), and it removes its containers, temporary database, and uploaded media after every run. Docker must be running; install the browser once after installing dependencies:

```sh
cd e2e
npm install
npx playwright install chromium
npm test
```

The default run uses deterministic fake AI and images and is the browser regression check used by pull requests. To explicitly validate live meal generation, food matching, activity classification, and all three generated meal images:

```sh
cd e2e
OPENAI_API_KEY=your-key npm run test:live
```

In PowerShell, set the key first with `$env:OPENAI_API_KEY = "your-key"`. The live suite incurs API usage and is only available through the manually dispatched **Live AI Browser E2E** GitHub Actions workflow. Add `OPENAI_API_KEY` as a repository Actions secret before running it. Failure traces, screenshots, videos, and the HTML report are retained as workflow artifacts.
