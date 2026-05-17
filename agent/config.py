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
