#!/usr/bin/env bash
# Repeatable deploy for the single-user MVP: backend to Cloud Run, frontend-v2 to
# Firebase Hosting. One-time resource creation is documented in the README "Deploy" section.
#
#   ./deploy.sh                 # deploy both
#   ./deploy.sh --backend-only
#   ./deploy.sh --frontend-only

set -euo pipefail

PROJECT_ID="recovery-meal"
REGION="us-central1"
SERVICE="recovery-meal-api"
REPO="recovery-meal"
BUCKET="recovery-meal-media"
BACKEND_ONLY=false
FRONTEND_ONLY=false

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --project-id PROJECT_ID   GCP project ID (default: recovery-meal)
  --region REGION           GCP region (default: us-central1)
  --service SERVICE         Cloud Run service name (default: recovery-meal-api)
  --repo REPO               Artifact registry repository (default: recovery-meal)
  --bucket BUCKET           Cloud Storage bucket for media uploads (default: recovery-meal-media)
  --backend-only            Deploy only the backend
  --frontend-only           Deploy only the frontend
  -h, --help                Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id)
      PROJECT_ID="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --service)
      SERVICE="$2"
      shift 2
      ;;
    --repo)
      REPO="$2"
      shift 2
      ;;
    --bucket)
      BUCKET="$2"
      shift 2
      ;;
    --backend-only)
      BACKEND_ONLY=true
      shift
      ;;
    --frontend-only)
      FRONTEND_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ACCOUNT="recovery-meal-api@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}"
SHA="$(git -C "$ROOT_DIR" rev-parse --short HEAD | tr -d '\n')"

printf 'project=%s region=%s service=%s tag=%s\n' "$PROJECT_ID" "$REGION" "$SERVICE" "$SHA"

if [[ "$FRONTEND_ONLY" != true ]]; then
  printf '\n== Building backend image ==\n'
  docker build --platform linux/amd64 -t "${IMAGE}:${SHA}" -t "${IMAGE}:latest" "$ROOT_DIR/backend"
  docker push "${IMAGE}:${SHA}"
  docker push "${IMAGE}:latest"

  printf '\n== Deploying Cloud Run ==\n'
  gcloud run deploy "$SERVICE" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --image="${IMAGE}:${SHA}" \
    --service-account="$SERVICE_ACCOUNT" \
    --allow-unauthenticated \
    --min-instances=0 \
    --max-instances=1 \
    --memory=1Gi \
    --cpu=1 \
    --timeout=120s \
    --set-secrets="DATABASE_URL=DATABASE_URL:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest" \
    --set-env-vars="APP_ENV=production,AI_MODE=live,IMAGE_MODE=live,UPLOAD_DIR=/app/uploads" \
    --add-volume="name=media,type=cloud-storage,bucket=${BUCKET}" \
    ## //app/uploads tells Git Bash to bypass its automatic path translation in Windows
    --volume-mount="name=media,mount-path=//app/uploads"

  URL=$(gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --format="value(status.url)" | tr -d '\n')
  printf 'API: %s\n' "$URL"
  curl -fsS "$URL/health"
  printf '\n'
fi

if [[ "$BACKEND_ONLY" != true ]]; then
  printf '\n== Building frontend-v2 ==\n'
  pushd "$ROOT_DIR/frontend-v2" > /dev/null
  if [[ ! -d node_modules ]]; then
    npm ci
  fi
  npm run build
  popd > /dev/null

  printf '\n== Deploying Firebase Hosting ==\n'
  firebase deploy --only hosting --project "$PROJECT_ID"
  printf 'UI: https://%s.web.app\n' "$PROJECT_ID"
fi

printf '\nDone.\n'
