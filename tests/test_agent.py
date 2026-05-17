import pytest
import asyncio

from agent.orchestrator import handle_problem
from agent.self_learn.runbook_updater import update_runbook
from agent.tools.agent_builder import get_grounding_context
from agent.tools.gemini_diagnosis import diagnose_problem
from agent.tools.remediation import execute_remediation


def test_handle_problem_returns_incident(sample_problem):
    result = asyncio.run(handle_problem(sample_problem["problem"]))

    assert result["incident"]["problem_id"] == sample_problem["problem"]["problemId"]
    assert result["analysis"]["diagnosis"]["recommended_action"] in {
        "scale_service",
        "publish_alert",
        "restart_service",
    }


def test_diagnosis_shape(sample_problem):
    diagnosis = diagnose_problem(
        sample_problem["problem"],
        sample_problem["entities"],
        sample_problem["metrics"],
        sample_problem["logs"],
        sample_problem["davis_context"],
    )

    assert set(diagnosis) == {
        "root_cause",
        "root_cause_explanation",
        "recommended_action",
        "confidence",
    }
    assert 0 <= diagnosis["confidence"] <= 1


def test_agent_builder_grounding_demo_context(sample_problem):
    context = get_grounding_context(sample_problem["problem"], {"traffic_spike": {}})

    assert context["source"] == "agent_builder_demo"
    assert "traffic_spike" in context["summary"]


def test_remediation_selects_known_action(sample_problem):
    result = asyncio.run(execute_remediation(
        "scale_service",
        sample_problem["problem"],
        sample_problem["entities"],
        {"root_cause": "traffic_spike"},
    ))

    assert result["action"] == "scale_service"


def test_runbook_update_creates_patterns():
    runbook = update_runbook()

    assert runbook
    assert all("recommended_action" in entry for entry in runbook.values())
