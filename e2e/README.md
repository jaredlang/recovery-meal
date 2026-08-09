# Recovery Meal Browser E2E Tests

This directory contains the Playwright/Chromium end-to-end test for the V2 application. Unlike the Vitest component tests, it uses the real V2 frontend, FastAPI backend, and PostgreSQL database.

Every run uses an isolated Docker Compose stack:

- V2 application: <http://127.0.0.1:5184>
- API health endpoint: <http://127.0.0.1:8010/health>
- PostgreSQL and uploaded media: temporary and removed during cleanup

## Prerequisites

- Docker Desktop or another Docker Compose-compatible runtime
- Node.js 20 or later
- npm

Install the test dependencies and Chromium once:

```sh
cd e2e
npm install
npx playwright install chromium
```

On Linux CI hosts, install Chromium and its operating-system dependencies with:

```sh
npx playwright install --with-deps chromium
```

## Automated browser test

Run the deterministic full-stack journey:

```sh
npm test
```

This command builds and starts the isolated application stack, runs the test with fake AI and fake images, and removes all E2E containers and temporary data afterward.

To validate the real model integrations, set `OPENAI_API_KEY` and run:

```sh
npm run test:live
```

PowerShell example:

```powershell
$env:OPENAI_API_KEY = "your-key"
npm run test:live
```

The live test makes real activity-classification, food-matching, meal-generation, and three image-generation requests. It incurs API usage and can take several minutes.

## Manual browser testing

Manual testing uses the same disposable stack but leaves it running while you interact with the application.

### 1. Start a clean deterministic stack

From the `e2e` directory, remove any stale E2E resources and start the services:

```sh
docker compose -f ../docker-compose.e2e.yml down --volumes --remove-orphans
docker compose -f ../docker-compose.e2e.yml up --build --wait
```

Confirm that the API reports `{"status":"ok"}` at <http://127.0.0.1:8010/health>, then open <http://127.0.0.1:5184> in a web browser.

### 2. Complete the user journey

1. On the welcome screen, select **Create profile**.
2. Enter a display name, email, age, height, weight, fitness goal, and maximum preparation time. Add favorite foods and foods to avoid, then select **Save changes**.
3. Open **Pantry** and add `chicken`, `brown rice`, and `banana`.
4. Open **Get Meal**, choose the file [`fixtures/workout.gpx`](fixtures/workout.gpx), and wait for the workout review screen.
5. Set the activity to **Running** and duration to `45` minutes.
6. Enter `70` kg as the pre-workout weight and `69.5` kg as the post-workout weight.
7. Select **Calculate recovery & continue** and confirm that protein, carbohydrate, and hydration targets appear.
8. Select **Generate meal options** and verify that three meals and three loaded images appear.
9. Favorite the first meal, select it, and verify its recipe, ingredients, preparation steps, nutrition, and image.
10. Open **Favorites** and confirm that the meal is present.
11. Open **Home** and confirm that the latest workout and selected recovery meal are displayed.
12. Open **Progress** and confirm that today's workout, selected meal, and one-day streak are displayed.

### 3. Optional failure checks

- Upload a non-GPX file and confirm that the application displays a readable validation error.
- Leave the activity as **Unknown** and confirm that continuing is disabled.
- Fill only one hydration weight and confirm that continuing is disabled.
- Refresh the workout review, meal options, recipe, Favorites, Home, and Progress pages to confirm that server-backed state persists.

### 4. Inspect service logs

If a request fails, inspect all service logs from another terminal:

```sh
docker compose -f ../docker-compose.e2e.yml logs --follow
```

To inspect one service, append `frontend-v2`, `backend`, or `db` to the command.

### 5. Stop and erase the manual test environment

Always remove the temporary database and uploads when finished:

```sh
docker compose -f ../docker-compose.e2e.yml down --volumes --remove-orphans
```

This command affects only resources owned by the `recovery-meal-e2e` Compose project. It does not remove development-stack data.

## Test artifacts and screenshots

Each successful journey attaches eight full-page checkpoint screenshots to the Playwright report:

1. `01-profile-saved.png`
2. `02-pantry-populated.png`
3. `03-workout-review.png`
4. `04-meal-options.png`
5. `05-meal-detail.png`
6. `06-favorites.png`
7. `07-home-dashboard.png`
8. `08-progress.png`

The screenshots capture the complete web page viewport context with `fullPage: true`; browser chrome is not included. Test runs retain evidence under:

- `test-results/`: checkpoint screenshots, trace, screenshot, video, and error context
- `playwright-report/`: HTML report

Open the HTML report with:

```sh
npx playwright show-report
```

Open an individual trace with:

```sh
npx playwright show-trace test-results/<test-directory>/trace.zip
```

Both artifact directories are ignored by Git. GitHub Actions uploads them for successful and failed automated browser tests.
