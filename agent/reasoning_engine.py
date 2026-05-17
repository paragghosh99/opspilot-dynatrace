from __future__ import annotations

from typing import Any

from agent.self_learn.runbook_updater import get_runbook
from agent.tools.agent_builder import get_grounding_context
from agent.tools.dynatrace_mcp import get_correlated_entities, get_davis_context, get_logs, get_metrics
from agent.tools.gemini_diagnosis import diagnose_problem


class OpsPilotAgent:
    def __init__(self, agent_builder_engine_id: str = ""):
        self.agent_builder_engine_id = agent_builder_engine_id

    async def analyze_problem(self, problem: dict[str, Any]) -> dict[str, Any]:
        problem_id = problem["problemId"]
        entities = await get_correlated_entities(problem_id)
        entity_ids = [entity.get("entityId", entity.get("id", "")) for entity in entities]
        metrics = await get_metrics(problem_id, entity_ids)
        logs = await get_logs(problem_id, entity_ids)
        davis_context = await get_davis_context(problem_id)
        runbook = get_runbook()
        grounding_context = get_grounding_context(problem, runbook)
        diagnosis = diagnose_problem(
            problem,
            entities,
            metrics,
            logs,
            {**davis_context, "agent_builder_grounding": grounding_context, "learned_runbook": runbook},
        )
        return {
            "problem": problem,
            "entities": entities,
            "metrics": metrics,
            "logs": logs,
            "davis_context": davis_context,
            "agent_builder_grounding": grounding_context,
            "diagnosis": diagnosis,
        }
