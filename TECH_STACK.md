# TECH_STACK

Compliance-verified technologies for OpsPilot.

## Required Core

- Google Cloud Agent Builder
- Gemini 2.5 Pro via Vertex AI
- Vertex AI Reasoning Engine
- Dynatrace MCP server
- OpenTelemetry

## Google Cloud Services

- Cloud Run
- Cloud Scheduler
- Secret Manager
- Cloud Storage
- Pub/Sub
- Cloud Build
- Vertex AI Search and Conversation

## Application Runtime

- Python
- FastAPI
- httpx
- pytest

## Compliance Notes

- Dynatrace MCP is the primary observability integration and is called by the agent workflow.
- Secrets are loaded from Secret Manager or environment variables.
- Local demo data is used only when cloud credentials are absent.
