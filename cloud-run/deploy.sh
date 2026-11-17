#!/usr/bin/env bash
# Builds and deploys the gatekeeper to Cloud Run. One-time setup is in README.md ("Deploy").
#
#   bash deploy.sh
#
# Override with PROJECT, REGION, SERVICE, SERVICE_ACCOUNT or MAX_INSTANCES in the environment.
set -euo pipefail
cd "$(dirname "$0")"

PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-gatekeeper}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-gatekeeper@${PROJECT}.iam.gserviceaccount.com}"
MAX_INSTANCES="${MAX_INSTANCES:-2}"
ENV_FILE=".env.production.yaml"

# Secret Manager names. Each one needs the service account as secretAccessor.
SECRETS="LIVEKIT_API_SECRET=livekit-api-secret:latest"
SECRETS+=",AGENT_SIGNING_SECRET=agent-signing-secret:latest"
SECRETS+=",SMTP_PASSWORD=smtp-password:latest"
SECRETS+=",ADMIN_EMAIL=admin-email:latest"

fail() { echo "deploy: $*" >&2; exit 1; }

[ -n "$PROJECT" ] || fail "no project. Set PROJECT or run: gcloud config set project <id>"
[ -f "$ENV_FILE" ] || fail "missing $ENV_FILE. See README.md (Deploy)."
[ -f .gcloudignore ] || fail "missing .gcloudignore, which keeps .env out of the upload."

# Secrets come from Secret Manager only, and Cloud Run uses the service's own identity.
if grep -Eq '^[[:space:]]*(LIVEKIT_API_SECRET|AGENT_SIGNING_SECRET|SMTP_PASSWORD|ADMIN_EMAIL|GOOGLE_APPLICATION_CREDENTIALS)[[:space:]]*:' "$ENV_FILE"; then
  fail "$ENV_FILE sets a secret or GOOGLE_APPLICATION_CREDENTIALS. Remove it; secrets go in Secret Manager."
fi

echo "Deploying $SERVICE to $PROJECT ($REGION), max $MAX_INSTANCES instances"

# --allow-unauthenticated: the API is public, and the app checks invite codes, admin
# sign-ins and signatures itself.
gcloud run deploy "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --source . \
  --service-account "$SERVICE_ACCOUNT" \
  --max-instances "$MAX_INSTANCES" \
  --allow-unauthenticated \
  --env-vars-file "$ENV_FILE" \
  --set-secrets "$SECRETS"

URL=$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --format 'value(status.url)')
echo "Deployed: $URL"
curl -fsS "$URL/health" && echo
