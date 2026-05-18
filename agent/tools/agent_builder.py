from __future__ import annotations

import uuid
from typing import Any

from agent import config

import httpx
import google.auth
from google.auth.transport.requests import Request

try:
    from google.cloud import discoveryengine_v1 as discoveryengine
except ImportError:
    discoveryengine = None


class AgentBuilderError(RuntimeError):
    pass


def _serving_config_path(engine_id: str) -> str:
    return (
        f"projects/{config.PROJECT_ID}/locations/{config.LOCATION}/"
        f"collections/default_collection/engines/{engine_id}/servingConfigs/default_config"
    )


def _fallback_grounding(source: str, runbook: dict[str, Any] | None = None, detail: str = "") -> dict[str, Any]:
    root_hints = ", ".join(sorted((runbook or {}).keys())) or "traffic_spike, dependency_failure, memory_leak"
    summary = (
        "OpsPilot is using the learned runbook as fallback grounding for known "
        f"root-cause categories: {root_hints}."
    )
    if detail:
        summary = f"{summary} Grounding detail: {detail}"
    return {"source": source, "summary": summary, "citations": ["learned-runbook-fallback"]}


def _access_token() -> str:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(Request())
    return credentials.token


def _conversational_agent_context(agent_path: str, problem: dict[str, Any]) -> dict[str, Any]:
    session_id = f"opspilot-{uuid.uuid4().hex}"
    session = f"{agent_path}/sessions/{session_id}"
    location = agent_path.split("/locations/", 1)[1].split("/", 1)[0]
    url = f"https://{location}-dialogflow.googleapis.com/v3/{session}:detectIntent"
    query = (
        "Provide concise SRE grounding for this Dynatrace incident. "
        f"Title: {problem.get('title', 'unknown')}. "
        f"Severity: {problem.get('severityLevel', 'UNKNOWN')}. "
        f"Problem ID: {problem.get('problemId', 'unknown')}."
    )
    payload = {
        "queryInput": {
            "text": {"text": query},
            "languageCode": "en",
        }
    }
    response = httpx.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {_access_token()}"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    messages = data.get("queryResult", {}).get("responseMessages", [])
    text = " ".join(
        part
        for message in messages
        for part in message.get("text", {}).get("text", [])
        if isinstance(part, str)
    )
    return {
        "source": "google_conversational_agent",
        "agent": agent_path,
        "summary": text or data.get("queryResult", {}).get("intent", {}).get("displayName", "Conversational Agent responded."),
        "citations": ["google-conversational-agent"],
    }


def get_grounding_context(problem: dict[str, Any], runbook: dict[str, Any] | None = None) -> dict[str, Any]:
    if config.DEMO_MODE:
        root_hints = ", ".join(sorted((runbook or {}).keys())) or "traffic_spike, dependency_failure, memory_leak"
        return {
            "source": "agent_builder_demo",
            "summary": (
                "Grounding context includes SRE playbooks, historical runbook patterns, "
                f"and known root-cause categories: {root_hints}."
            ),
            "citations": ["incident-response-runbook", "dynatrace-davis-patterns"],
        }

    if not config.AGENT_BUILDER_ENGINE_ID:
        return _fallback_grounding("agent_builder_not_configured", runbook)

    if "/agents/" in config.AGENT_BUILDER_ENGINE_ID:
        try:
            return _conversational_agent_context(config.AGENT_BUILDER_ENGINE_ID, problem)
        except Exception as exc:
            return _fallback_grounding("google_conversational_agent_error", runbook, str(exc))

    if discoveryengine is None:
        raise AgentBuilderError("google-cloud-discoveryengine is required outside demo mode")

    try:
        client = discoveryengine.SearchServiceClient()
        request = discoveryengine.SearchRequest(
            serving_config=_serving_config_path(config.AGENT_BUILDER_ENGINE_ID),
            query=problem.get("title", ""),
            page_size=3,
        )
        response = client.search(request=request)
    except Exception as exc:
        return _fallback_grounding("google_cloud_agent_builder_error", runbook, str(exc))

    snippets = []
    for result in response.results:
        document = result.document
        derived = document.derived_struct_data or {}
        snippets.append(
            {
                "id": document.id,
                "title": derived.get("title", document.name),
                "snippet": derived.get("extractive_answers", derived.get("snippets", [])),
            }
        )
    return {"source": "google_cloud_agent_builder", "results": snippets}
