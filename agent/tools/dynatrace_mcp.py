from __future__ import annotations

import json
import os
from typing import Any

import httpx
try:
    from google.cloud import secretmanager
except ImportError:  # Allows local demo mode before cloud dependencies are installed.
    secretmanager = None

try:
    from opentelemetry import trace
except ImportError:
    trace = None

from agent import config


tracer = trace.get_tracer(__name__) if trace else None


class DynatraceMCPError(RuntimeError):
    pass


def _secret_value(secret_name: str) -> str:
    if secretmanager is None:
        raise DynatraceMCPError("google-cloud-secret-manager is required outside demo mode")
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{config.PROJECT_ID}/secrets/{secret_name}/versions/latest"
    return client.access_secret_version(name=name).payload.data.decode("utf-8")


def get_dynatrace_credentials() -> tuple[str, str]:
    env_url = os.getenv("DYNATRACE_ENV_URL")
    token = os.getenv("DYNATRACE_API_TOKEN")
    if env_url and token:
        return env_url.rstrip("/"), token

    env_secret = os.getenv("DYNATRACE_ENV_URL_SECRET", "DYNATRACE_ENV_URL")
    token_secret = os.getenv("DYNATRACE_API_TOKEN_SECRET", "DYNATRACE_API_TOKEN")
    return _secret_value(env_secret).rstrip("/"), _secret_value(token_secret)


def _load_demo_problem() -> dict[str, Any]:
    return json.loads(config.FIXTURE_PROBLEM.read_text(encoding="utf-8"))


async def _call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    if tracer:
        with tracer.start_as_current_span(f"dynatrace.mcp.{tool_name}"):
            return await _call_mcp_tool_untraced(tool_name, arguments)
    return await _call_mcp_tool_untraced(tool_name, arguments)


async def _call_mcp_tool_untraced(tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    if config.DEMO_MODE:
        problem = _load_demo_problem()
        demo_payloads = {
            "get_problems": [problem["problem"]],
            "get_entities": problem["entities"],
            "get_metrics": [problem["metrics"]],
            "get_logs": problem["logs"],
            "get_davis_context": [problem["davis_context"]],
        }
        return demo_payloads.get(tool_name, [])

    env_url, token = get_dynatrace_credentials()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{env_url}/mcp",
            json={
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            headers={"Authorization": f"Api-Token {token}"},
        )
    if response.status_code >= 400:
        raise DynatraceMCPError(f"{tool_name} failed with HTTP {response.status_code}")
    payload = response.json()
    content = payload.get("content", [])
    return content if isinstance(content, list) else [content]


async def get_open_problems() -> list[dict[str, Any]]:
    return await _call_mcp_tool(
        "get_problems",
        {"status": "OPEN", "fields": "problemId,title,severityLevel,entityNames,startTime,problemUrl"},
    )


async def get_correlated_entities(problem_id: str) -> list[dict[str, Any]]:
    return await _call_mcp_tool("get_entities", {"problemId": problem_id})


async def get_metrics(problem_id: str, entity_ids: list[str]) -> dict[str, Any]:
    rows = await _call_mcp_tool("get_metrics", {"problemId": problem_id, "entityIds": entity_ids})
    return rows[0] if rows else {}


async def get_logs(problem_id: str, entity_ids: list[str]) -> list[dict[str, Any]]:
    return await _call_mcp_tool("get_logs", {"problemId": problem_id, "entityIds": entity_ids, "limit": 25})


async def get_davis_context(problem_id: str) -> dict[str, Any]:
    rows = await _call_mcp_tool("get_davis_context", {"problemId": problem_id})
    return rows[0] if rows else {}
