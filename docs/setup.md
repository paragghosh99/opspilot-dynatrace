# Setup

## Google Cloud

```bash
gcloud config set project opspilot-hackathon-2026
gcloud services enable \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  discoveryengine.googleapis.com
```

## Secrets

```bash
echo -n "https://your-environment.live.dynatrace.com" | gcloud secrets create DYNATRACE_ENV_URL --data-file=-
echo -n "your-token" | gcloud secrets create DYNATRACE_API_TOKEN --data-file=-
```

## Local Demo

```bash
pip install -r requirements.txt
cd web
npm install
npm run build
cd ..
uvicorn api.main:app --reload
```

The app uses fixture data when `DEMO_MODE=true` or Dynatrace credentials are absent.

## Gemini Billing

OpsPilot must use Gemini only through Vertex AI so calls are billed to the Google Cloud project. Do not configure `GEMINI_API_KEY` or `GOOGLE_API_KEY`. Production deployments should set:

```bash
GCP_PROJECT_ID=opspilot-hackathon-2026
GCP_LOCATION=us-central1
DEMO_MODE=false
```
