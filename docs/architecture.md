# Architecture

OpsPilot has four layers.

## Detection

Cloud Scheduler calls `/poll` every two minutes. The FastAPI route asks the Dynatrace MCP server for open problems and deduplicates problem IDs.

## Intelligence

`OpsPilotAgent` gathers entities, metrics, logs, and Davis context through MCP calls. It then asks Google Cloud Agent Builder for grounding context from the configured incident-response data store. Gemini on Vertex AI receives the Dynatrace context, Davis context, Agent Builder grounding, and learned runbook before returning a structured diagnosis with root cause, explanation, confidence, and recommended action.

## Action

The remediation module maps diagnosis output to one of three actions:

- scale a Cloud Run service
- publish a Pub/Sub alert
- call a restart webhook

## Persistence

Incident records and learned runbook patterns are stored in Cloud Storage in production. Local demo mode stores JSON under `.opspilot/`.
