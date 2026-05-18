#!/usr/bin/env bash
set -euo pipefail

gcloud run deploy opspilot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --set-env-vars GCP_PROJECT_ID=opspilot-496509,GCP_LOCATION=us-central1,GEMINI_MODEL=gemini-2.5-pro,DEMO_MODE=false,INCIDENT_BUCKET=opspilot-incidents-opspilot-496509,PUBSUB_TOPIC=opspilot-incidents,DYNATRACE_ENV_URL_SECRET=DYNATRACE_ENV_URL,DYNATRACE_API_TOKEN_SECRET=DYNATRACE_API_TOKEN
