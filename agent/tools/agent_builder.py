from __future__ import annotations

from typing import Any

from agent import config

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
        raise AgentBuilderError("AGENT_BUILDER_ENGINE_ID is required outside demo mode")
    if discoveryengine is None:
        raise AgentBuilderError("google-cloud-discoveryengine is required outside demo mode")

    client = discoveryengine.SearchServiceClient()
    request = discoveryengine.SearchRequest(
        serving_config=_serving_config_path(config.AGENT_BUILDER_ENGINE_ID),
        query=problem.get("title", ""),
        page_size=3,
    )
    response = client.search(request=request)
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
