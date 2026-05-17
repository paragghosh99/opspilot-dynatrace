from __future__ import annotations

import json
from typing import Any

try:
    import vertexai
    from vertexai.preview.generative_models import GenerativeModel
except ImportError:
    vertexai = None
    GenerativeModel = None

from agent import config


class DiagnosisFormatError(RuntimeError):
    pass


def _demo_diagnosis(problem: dict[str, Any], metrics: dict[str, Any], logs: list[dict[str, Any]]) -> dict[str, Any]:
    title = problem.get("title", "").lower()
    cpu = float(metrics.get("cpu_utilization", 0))
    memory = float(metrics.get("memory_utilization", 0))
    error_rate = float(metrics.get("error_rate", 0))

    if memory >= 85:
        cause = "memory_leak"
        action = "restart_service"
    elif cpu >= 80 or "traffic" in title:
        cause = "traffic_spike"
        action = "scale_service"
    elif error_rate >= 5 or any("timeout" in str(row).lower() for row in logs):
        cause = "dependency_failure"
        action = "publish_alert"
    else:
        cause = "unknown"
        action = "publish_alert"

    return {
        "root_cause": cause,
        "root_cause_explanation": (
            "Dynatrace metrics and log patterns indicate the service is under abnormal pressure. "
            "The selected action is scoped to reduce impact while preserving an audit trail."
        ),
        "recommended_action": action,
        "confidence": 0.84,
    }


def diagnose_problem(
    problem: dict[str, Any],
    entities: list[dict[str, Any]],
    metrics: dict[str, Any],
    logs: list[dict[str, Any]],
    davis_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if config.DEMO_MODE:
        return _demo_diagnosis(problem, metrics, logs)
    if vertexai is None or GenerativeModel is None:
        raise RuntimeError("google-cloud-aiplatform is required outside demo mode")

    config.validate_vertex_ai_billing_config()
    vertexai.init(project=config.PROJECT_ID, location=config.LOCATION)
    model = GenerativeModel("gemini-2.5-pro-preview-05-06")
    entity_names = [item.get("entityName", item.get("displayName", "unknown")) for item in entities]
    prompt = f"""
You are OpsPilot, an autonomous SRE incident response agent. Analyze the Dynatrace problem and return only valid JSON.

Problem: {json.dumps(problem, sort_keys=True)}
Affected entities: {json.dumps(entity_names)}
Metrics: {json.dumps(metrics, sort_keys=True)}
Recent logs: {json.dumps(logs[:10], sort_keys=True)}
Davis context: {json.dumps(davis_context or {}, sort_keys=True)}

Return a JSON object with:
- root_cause: one of memory_leak, traffic_spike, dependency_failure, config_error, unknown
- root_cause_explanation: two short sentences
- recommended_action: one of scale_service, publish_alert, restart_service
- confidence: number from 0.0 to 1.0
"""
    response = model.generate_content(prompt)
    try:
        diagnosis = json.loads(response.text.strip())
    except json.JSONDecodeError as exc:
        raise DiagnosisFormatError("Gemini response was not valid JSON") from exc

    required = {"root_cause", "root_cause_explanation", "recommended_action", "confidence"}
    if not required.issubset(diagnosis):
        raise DiagnosisFormatError("Gemini diagnosis is missing required keys")
    return diagnosis
