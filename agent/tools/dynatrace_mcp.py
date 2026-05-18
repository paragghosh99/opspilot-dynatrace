from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse

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


def _mcp_url(env_url: str) -> str:
    if env_url.endswith("/mcp"):
        return env_url
    parsed = urlparse(env_url)
    if not parsed.scheme or not parsed.netloc:
        raise DynatraceMCPError("DYNATRACE_ENV_URL must be a full https://... Dynatrace platform URL")
    return f"{parsed.scheme}://{parsed.netloc}/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp"


def _load_demo_problem() -> dict[str, Any]:
    return json.loads(config.FIXTURE_PROBLEM.read_text(encoding="utf-8"))


def _parse_mcp_content(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if "error" in payload:
        raise DynatraceMCPError(str(payload["error"]))

    result = payload.get("result", payload)
    structured = result.get("structuredContent", {})
    records = structured.get("records")
    if isinstance(records, list):
        return [row for row in records if isinstance(row, dict)]

    content = result.get("content", result if isinstance(result, list) else [])
    if not isinstance(content, list):
        content = [content]

    rows: list[dict[str, Any]] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                rows.append({"text": text})
                continue
            if isinstance(decoded, list):
                rows.extend(row for row in decoded if isinstance(row, dict))
            elif isinstance(decoded, dict):
                rows.append(decoded)
        elif isinstance(item, dict):
            rows.append(item)
    return rows


def _entity_type(entity_id: str) -> str:
    prefix = entity_id.split("-", 1)[0].lower()
    return f"dt.entity.{prefix}"


def _normalize_problem(row: dict[str, Any], env_url: str | None = None) -> dict[str, Any]:
    problem_id = row.get("problemId") or row.get("display_id") or row.get("event.id") or row.get("event_id")
    title = row.get("title") or row.get("event.description") or row.get("event.category") or "Dynatrace problem"
    entity_ids = row.get("affected_entity_ids") or row.get("related_entity_ids") or row.get("entityIds") or []
    if not isinstance(entity_ids, list):
        entity_ids = [entity_ids]

    normalized = {
        "problemId": problem_id,
        "title": title,
        "severityLevel": row.get("severityLevel") or row.get("event.category") or row.get("event.status") or "UNKNOWN",
        "entityNames": row.get("entityNames") or entity_ids,
        "startTime": row.get("startTime") or row.get("event.start"),
        "problemUrl": row.get("problemUrl"),
        "affected_entity_ids": entity_ids,
    }
    if not normalized["problemUrl"] and env_url and problem_id:
        normalized["problemUrl"] = f"{env_url.rstrip('/')}/ui/apps/dynatrace.classic.problems/#problems/problemdetails;pid={problem_id}"
    return {key: value for key, value in normalized.items() if value is not None}


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
            "list_problems": [problem["problem"]],
            "get_entities": problem["entities"],
            "find_entity_by_name": problem["entities"],
            "get_metrics": [problem["metrics"]],
            "execute_dql": [problem["metrics"]],
            "get_logs": problem["logs"],
            "get_davis_context": [problem["davis_context"]],
            "chat_with_davis_copilot": [problem["davis_context"]],
        }
        return demo_payloads.get(tool_name, [])

    env_url, token = get_dynatrace_credentials()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            _mcp_url(env_url),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json, text/event-stream",
            },
        )
    if response.status_code >= 400:
        raise DynatraceMCPError(f"{tool_name} failed with HTTP {response.status_code}")
    return _parse_mcp_content(response.json())


async def get_open_problems() -> list[dict[str, Any]]:
    if config.DEMO_MODE:
        return await _call_mcp_tool(
            "get_problems",
            {"status": "OPEN", "fields": "problemId,title,severityLevel,entityNames,startTime,problemUrl"},
        )
    env_url, _ = get_dynatrace_credentials()
    rows = await _call_mcp_tool(
        os.getenv("DYNATRACE_MCP_PROBLEMS_TOOL", "query-problems"),
        {"status": "ACTIVE", "history": os.getenv("DYNATRACE_PROBLEM_HISTORY", "2d"), "includeTypes": False},
    )
    return [_normalize_problem(row, env_url) for row in rows]


async def get_correlated_entities(problem_id: str) -> list[dict[str, Any]]:
    if config.DEMO_MODE:
        return await _call_mcp_tool("get_entities", {"problemId": problem_id})
    rows = await _call_mcp_tool(
        os.getenv("DYNATRACE_MCP_PROBLEM_DETAILS_TOOL", "get-problem-by-id"),
        {"problemId": problem_id, "history": os.getenv("DYNATRACE_PROBLEM_HISTORY", "2d"), "includeTypes": False},
    )
    entities: list[dict[str, Any]] = []
    for row in rows:
        for entity_id in row.get("affected_entity_ids", []) or row.get("related_entity_ids", []) or []:
            entities.append({"entityId": entity_id, "entityName": entity_id, "type": _entity_type(entity_id)})
    return entities


async def get_metrics(problem_id: str, entity_ids: list[str]) -> dict[str, Any]:
    if config.DEMO_MODE:
        rows = await _call_mcp_tool("get_metrics", {"problemId": problem_id, "entityIds": entity_ids})
        return rows[0] if rows else {}
    rows = await _call_mcp_tool(
        os.getenv("DYNATRACE_MCP_METRICS_TOOL", "execute-dql"),
        {"dqlQueryString": f"fetch dt.davis.problems | filter display_id == \"{problem_id}\" or event.id == \"{problem_id}\" | limit 10", "includeTypes": False},
    )
    return rows[0] if rows else {}


async def get_logs(problem_id: str, entity_ids: list[str]) -> list[dict[str, Any]]:
    if config.DEMO_MODE:
        return await _call_mcp_tool("get_logs", {"problemId": problem_id, "entityIds": entity_ids, "limit": 25})
    return await _call_mcp_tool(
        os.getenv("DYNATRACE_MCP_LOGS_TOOL", "execute-dql"),
        {"dqlQueryString": "fetch logs | sort timestamp desc | limit 25", "includeTypes": False},
    )


async def get_davis_context(problem_id: str) -> dict[str, Any]:
    if config.DEMO_MODE:
        rows = await _call_mcp_tool("get_davis_context", {"problemId": problem_id})
        return rows[0] if rows else {}
    rows = await _call_mcp_tool(
        os.getenv("DYNATRACE_MCP_DAVIS_TOOL", "get-problem-by-id"),
        {"problemId": problem_id, "history": os.getenv("DYNATRACE_PROBLEM_HISTORY", "2d"), "includeTypes": False},
    )
    return rows[0] if rows else {}
