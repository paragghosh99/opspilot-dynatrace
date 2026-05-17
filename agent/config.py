from __future__ import annotations

import os
from pathlib import Path


PROJECT_ID = os.getenv("GCP_PROJECT_ID", "opspilot-hackathon-2026")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
INCIDENT_BUCKET = os.getenv("INCIDENT_BUCKET", "opspilot-incidents")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "opspilot-incidents")
AGENT_BUILDER_ENGINE_ID = os.getenv("AGENT_BUILDER_ENGINE_ID", "")
RESTART_WEBHOOK_URL = os.getenv("RESTART_WEBHOOK_URL", "")
DEMO_MODE = os.getenv("DEMO_MODE", "").lower() in {"1", "true", "yes"} or not os.getenv("DYNATRACE_ENV_URL")

ROOT_DIR = Path(__file__).resolve().parents[1]
LOCAL_STATE_DIR = ROOT_DIR / ".opspilot"
FIXTURE_PROBLEM = ROOT_DIR / "tests" / "fixtures" / "sample_problem.json"


def validate_vertex_ai_billing_config() -> None:
    if os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not allowed. OpsPilot must use Gemini through Vertex AI billing only.")
    if os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY is not allowed for Gemini. Use Vertex AI project/location configuration.")
    if not PROJECT_ID:
        raise RuntimeError("GCP_PROJECT_ID must be set for Vertex AI Gemini billing.")
    if not LOCATION:
        raise RuntimeError("GCP_LOCATION must be set for Vertex AI Gemini billing.")
