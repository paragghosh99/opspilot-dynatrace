from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
try:
    from google.cloud import pubsub_v1
except ImportError:
    pubsub_v1 = None

from agent import config


async def scale_cloud_run(service_name: str, min_instances: int = 2) -> dict[str, Any]:
    if config.DEMO_MODE:
        return {
            "action": "scale_service",
            "status": "simulated",
            "target": service_name,
            "min_instances": min_instances,
        }

    return {
        "action": "scale_service",
        "status": "queued",
        "target": service_name,
        "min_instances": min_instances,
        "note": "Apply with gcloud or Cloud Run Admin API in deployment.",
    }


async def publish_incident_alert(problem_id: str, diagnosis: dict[str, Any], severity: str) -> dict[str, Any]:
    message = {
        "problem_id": problem_id,
        "severity": severity,
        "diagnosis": diagnosis,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    if config.DEMO_MODE:
        return {"action": "publish_alert", "status": "simulated", "message": message}
    if pubsub_v1 is None:
        raise RuntimeError("google-cloud-pubsub is required outside demo mode")

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(config.PROJECT_ID, config.PUBSUB_TOPIC)
    future = publisher.publish(topic_path, str(message).encode("utf-8"))
    return {"action": "publish_alert", "status": "published", "message_id": future.result(timeout=15)}


async def call_restart_webhook(service_url: str) -> dict[str, Any]:
    if config.DEMO_MODE or not service_url:
        return {"action": "restart_service", "status": "simulated", "target": service_url or "demo-service"}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(service_url, json={"source": "opspilot"})
    return {"action": "restart_service", "status": "called", "http_status": response.status_code}


async def execute_remediation(
    recommended_action: str,
    problem: dict[str, Any],
    entities: list[dict[str, Any]],
    diagnosis: dict[str, Any],
) -> dict[str, Any]:
    service_name = entities[0].get("entityName", "checkout-service") if entities else "checkout-service"
    severity = problem.get("severityLevel", "UNKNOWN")
    problem_id = problem.get("problemId", "unknown")

    if recommended_action == "scale_service":
        return await scale_cloud_run(service_name, min_instances=3)
    if recommended_action == "restart_service":
        return await call_restart_webhook(config.RESTART_WEBHOOK_URL)
    return await publish_incident_alert(problem_id, diagnosis, severity)
