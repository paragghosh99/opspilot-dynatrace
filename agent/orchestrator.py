from __future__ import annotations

import json
from typing import Any

from agent import config
from agent.reasoning_engine import OpsPilotAgent
from agent.self_learn.incident_logger import log_incident
from agent.self_learn.runbook_updater import update_runbook
from agent.tools.dynatrace_mcp import get_open_problems
from agent.tools.remediation import execute_remediation


def _state_path():
    config.LOCAL_STATE_DIR.mkdir(parents=True, exist_ok=True)
    return config.LOCAL_STATE_DIR / "processed_ids.json"


def get_processed_ids() -> set[str]:
    if config.DEMO_MODE:
        path = _state_path()
        if not path.exists():
            return set()
        return set(json.loads(path.read_text(encoding="utf-8")))
    return set()


def save_processed_ids(processed_ids: set[str]) -> None:
    if config.DEMO_MODE:
        try:
            _state_path().write_text(json.dumps(sorted(processed_ids), indent=2), encoding="utf-8")
        except OSError:
            return


async def handle_problem(problem: dict[str, Any]) -> dict[str, Any]:
    agent = OpsPilotAgent(config.AGENT_BUILDER_ENGINE_ID)
    analysis = await agent.analyze_problem(problem)
    action_result = await execute_remediation(
        analysis["diagnosis"]["recommended_action"],
        problem,
        analysis["entities"],
        analysis["diagnosis"],
    )
    incident = log_incident(problem, analysis["diagnosis"], action_result, analysis["entities"])
    runbook = update_runbook()
    return {"incident": incident, "analysis": analysis, "action_result": action_result, "runbook": runbook}


async def poll_and_respond() -> dict[str, Any]:
    processed = get_processed_ids()
    problems = await get_open_problems()
    new_problems = [problem for problem in problems if problem.get("problemId") not in processed]
    handled = []
    for problem in new_problems:
        handled.append(await handle_problem(problem))
        processed.add(problem["problemId"])
    save_processed_ids(processed)
    return {"new_problems": len(new_problems), "handled": handled}
