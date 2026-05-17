import pytest
import asyncio

from agent.tools.dynatrace_mcp import get_correlated_entities, get_logs, get_metrics, get_open_problems


def test_get_open_problems_from_demo_fixture():
    problems = asyncio.run(get_open_problems())

    assert problems
    assert problems[0]["problemId"].startswith("P-")


def test_get_context_tools_from_demo_fixture():
    entities = asyncio.run(get_correlated_entities("P-240517-001"))
    metrics = asyncio.run(get_metrics("P-240517-001", ["SERVICE-CHECKOUT"]))
    logs = asyncio.run(get_logs("P-240517-001", ["SERVICE-CHECKOUT"]))

    assert entities[0]["entityName"] == "checkout-service"
    assert metrics["cpu_utilization"] > 0
    assert logs[0]["level"] in {"ERROR", "WARN", "INFO"}
