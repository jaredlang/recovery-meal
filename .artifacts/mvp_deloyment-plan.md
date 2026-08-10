# MVP Deployment Plan — Google Cloud + Supabase

Status: In progress — code changes done (Phases 2.3, 3, 4.2, 4.3, 5.2, 5.3); cloud work pending.
Goal: get the app off the local machine and onto a URL the author can use. Single profile,
no authentication, not a production launch.

## Target architecture

```text
Browser
  |
  v
Firebase Hosting  (static frontend-v2 build)
  |-- /api/**    rewrite --> Cloud Run
  |-- /media/**  rewrite --> Cloud Run
  |-- /**        rewrite --> /index.html
                                |
                                v
                        Cloud Run (FastAPI, max-instances=1, scales to zero)
                          |-- Secret Manager: DATABASE_URL, OPENAI_API_KEY
                          |-- GCS bucket mounted at /app/uploads
                          |-- Supabase PostgreSQL (session pooler)
```

Two choices do most of the simplifying work:

- **Everything behind Firebase Hosting.** The frontend calls `/api/v1` on its own origin, so CORS
  is never exercised and the Cloud Run URL never gets baked into the JS bundle.
- **`max-instances=1`.** No concurrent instances means no migration race, so
  `alembic upgrade head` stays in the container entrypoint where it already is, and there is no
  separate migration step to build or run.

`frontend/` (v1) is not deployed; it stays in the repo for reference.

---

## Phase 1 — Cloud setup

### Task 1.1 — Project, APIs, image repository

```sh
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com storage.googleapis.com firebasehosting.googleapis.com
gcloud artifacts repositories create recovery-meal \
  --repository-format=docker --location=us-central1
```

Pick one region and use it everywhere; `us-central1` is safe for Firebase Hosting → Cloud Run
rewrites.

**Done when** `gcloud auth configure-docker us-central1-docker.pkg.dev` succeeds.

### Task 1.2 — Media bucket

Cloud Run's disk is wiped on restart, so avatars and generated meal images must live outside the
container or the database will hold `image_status='ready'` rows pointing at nothing.

```sh
gcloud storage buckets create gs://<PROJECT_ID>-recovery-meal-media \
  --location=us-central1 --uniform-bucket-level-access
```

The Cloud Run runtime service account needs `roles/storage.objectAdmin` on this bucket and
`roles/secretmanager.secretAccessor` on both secrets.

**Done when** the bucket exists and the bindings are in place.

### Task 1.3 — Secrets

```sh
printf '%s' '<pooled-database-url>' | gcloud secrets create DATABASE_URL --data-file=-
printf '%s' '<openai-key>'          | gcloud secrets create OPENAI_API_KEY --data-file=-
```

The database URL comes from Task 2.1 — do that first, or update the secret afterwards.

---

## Phase 2 — Supabase

### Task 2.1 — Get a connection string that works from Cloud Run

Supabase Dashboard → Project Settings → Database → Connection string → **Session pooler**.

This matters: Supabase *direct* connections are IPv6-only and Cloud Run's default egress is
IPv4-only, so a direct URL just times out. The session pooler is IPv4 and supports prepared
statements, which psycopg3 turns on by itself after a query runs five times — the transaction
pooler (port 6543) would break on that. Using the session pooler means no code changes.

Adapt the copied URI:

- scheme `postgresql://` → `postgresql+psycopg://`
- append `?sslmode=require`
- percent-encode special characters in the password

**Done when** a local `alembic current` against that URL connects.

### Task 2.2 — Create the schema

```sh
cd backend
DATABASE_URL='<pooled-url>' alembic upgrade head
```

[backend/migrations/env.py:10](backend/migrations/env.py#L10) already prefers `DATABASE_URL`, so
nothing needs editing.

**Done when** Supabase shows `user_profile`, `inventory_item`, `workout`, `recommendation`,
`favorite_meal`.

### Task 2.3 — Survive idle pooler connections ✅

File: [backend/app/db/session.py](backend/app/db/session.py)

`pool_pre_ping=True` is already there. Add `pool_recycle=1800` — the pooler drops idle
connections, and without recycling the first request after an idle spell fails.

**Done:** added; `pytest` passes (12 tests).

---

## Phase 3 — Container changes

### Task 3.1 — Listen on `$PORT` ✅

File: [backend/Dockerfile](backend/Dockerfile)

The `CMD` hardcoded `--port 8000`; Cloud Run injects `PORT=8080` and would fail the startup probe.
The port now defaults to 8000 when unset so Docker Compose keeps working unchanged, and
`alembic upgrade head` stays in the command — with one instance it is the simplest place for it.

**Done:** verified against a throwaway Postgres container. With `PORT=8080` the migrations ran and
uvicorn bound 8080; with `PORT` unset it bound 8000. `/api/v1/profile` returned `PROFILE_REQUIRED`,
confirming the database round trip.

### Task 3.2 — Add a `.dockerignore` ✅

`COPY . .` shipped `.env`, local `uploads/`, `__pycache__`, and `.pytest_cache` into the image.

**Done:** [backend/.dockerignore](backend/.dockerignore) added; the built image contains no `.env`
and an empty `/app/uploads`.

---

## Phase 4 — Deploy

### Task 4.1 — Deploy the API to Cloud Run

Build for `linux/amd64`, push to Artifact Registry, then deploy with:

- both secrets wired as env vars from Secret Manager
- the bucket mounted at `/app/uploads`:
  `--add-volume=name=media,type=cloud-storage,bucket=<bucket>`
  `--add-volume-mount=volume=media,mount-path=/app/uploads`
- `--allow-unauthenticated --min-instances=0 --max-instances=1 --memory=1Gi --timeout=120s`
- `AI_MODE` / `IMAGE_MODE` set to `live` (image generation is the main per-request cost)

The mount is what makes media work with no code change: `Path(settings.upload_dir) / "media"` in
[backend/app/services/media.py:7](backend/app/services/media.py#L7), the `write_bytes` calls in
[recommendations.py:87](backend/app/api/v1/recommendations.py#L87) and
[profile.py:79](backend/app/api/v1/profile.py#L79), and the `StaticFiles` mount at
[main.py:35](backend/app/main.py#L35) all land on the bucket.

**Done when** `/health` returns ok and `/api/v1/profile` returns the `PROFILE_REQUIRED` 404 —
that 404 proves the Supabase round-trip works.

### Task 4.2 — Configure Firebase Hosting ✅

[firebase.json](firebase.json) sets `public: frontend-v2/dist` with rewrites in this order:

1. `/api/**` → Cloud Run service
2. `/media/**` → same service
3. `**` → `/index.html` — required, because
   [frontend-v2/src/router.tsx](frontend-v2/src/router.tsx#L3) uses `history.pushState` and a
   refresh on `/pantry` would 404 without it

Note that `/health` lives at the backend root, so it is caught by the SPA catch-all and is not
reachable through Hosting — check it on the Cloud Run URL directly.

`.firebaserc` still needs the project id.

**Done when** `firebase deploy --only hosting` publishes and
`https://<PROJECT_ID>.web.app/api/v1/profile` proxies through to Cloud Run.

### Task 4.3 — Point the frontend at its own origin ✅

[frontend-v2/.env.production](frontend-v2/.env.production) sets `VITE_API_URL=/api/v1`.

`VITE_API_URL` is read at build time ([frontend-v2/src/api.ts:3](frontend-v2/src/api.ts#L3)) and
`MEDIA` is derived by stripping the `/api/v1` suffix, which leaves it empty so `imageUrl` yields
same-origin `/media/...` paths.

**Done:** production build contains `"/api/v1"` and zero `localhost:8000` references.

### Task 4.4 — Walk the real journey

Profile → foods → GPX upload → activity/duration correction → weights → recovery → generate
meals → images → favorite → dashboard. Then redeploy a revision and confirm the images still
render (proves media is really in the bucket).

---

## Phase 5 — Wrap up

### Task 5.1 — Billing budget

A GCP budget (e.g. $20/month) with email alerts, plus a monthly cap on the OpenAI key. Cloud Run
at `min-instances=0` costs nothing idle; OpenAI image generation is the only real spend.

### Task 5.2 — One-command redeploy ✅

**Done:** [deploy.ps1](deploy.ps1) builds and pushes the backend image (tagged with the commit
SHA), deploys the Cloud Run revision with the full flag set, builds `frontend-v2`, and deploys
Hosting. `-BackendOnly` and `-FrontendOnly` skip halves. A script is enough here — GitHub Actions
and Workload Identity Federation are not worth the setup for a single-user deployment.

### Task 5.3 — Note it in the README ✅

**Done:** [README.md](README.md) has a "Deploy" section covering the architecture, one-time
resource setup, the session-pooler requirement, the deploy command, and rollback.

---

## Sequencing

| Phase | Depends on | Effort |
| --- | --- | --- |
| 1 — Cloud setup | — | 30 min |
| 2 — Supabase | 1 | 45 min |
| 3 — Container changes | — (parallel with 1–2) | 30 min |
| 4 — Deploy | 1, 2, 3 | 2 h |
| 5 — Wrap up | 4 | 45 min |

Phase 3 is code-only, so it was done first while the cloud resources are still being created.

## Deliberately deferred

Authentication and multi-user support, rate limiting, CI/CD, custom domain, uptime checks, and
database backups. Worth revisiting only if the app outgrows being a single-user tool — every
table already carries `profile_id`, so adding real users later is an auth layer plus
request-scoped profile lookup, not a data model rewrite.
