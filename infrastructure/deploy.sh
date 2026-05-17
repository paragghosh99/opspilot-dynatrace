#!/usr/bin/env bash
set -euo pipefail

gcloud run deploy opspilot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --set-env-vars GCP_PROJECT_ID=opspilot-hackathon-2026,GCP_LOCATION=us-central1,DEMO_MODE=false
