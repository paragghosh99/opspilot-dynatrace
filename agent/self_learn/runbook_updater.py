from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

try:
    from google.cloud import storage
except ImportError:
    storage = None

from agent import config
from agent.self_learn.incident_logger import list_incidents


RUNBOOK_KEY = "runbook/learned_patterns.json"


def update_runbook() -> dict[str, Any]:
    incidents = list_incidents()
    by_cause: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for incident in incidents:
        by_cause[incident.get("root_cause", "unknown")].append(incident)

    runbook = {}
    for cause, rows in by_cause.items():
        actions = [row.get("action_taken", "publish_alert") for row in rows]
        resolved = [row for row in rows if row.get("resolved")]
        action_counts = Counter(actions)
        recommended = action_counts.most_common(1)[0][0] if action_counts else "publish_alert"
        avg_mttr = sum(float(row.get("mttr_minutes", 0)) for row in resolved) / max(len(resolved), 1)
        success_rate = len(resolved) / len(rows) if rows else 0
        runbook[cause] = {
            "incident_count": len(rows),
            "recommended_action": recommended,
            "success_rate": round(success_rate * 100, 1),
            "avg_mttr_minutes": round(avg_mttr, 1),
            "summary": (
                f"When root cause is {cause.replace('_', ' ')}, OpsPilot most often succeeds with "
                f"{recommended.replace('_', ' ')} across {len(rows)} incidents."
            ),
            "contributing_incidents": [row.get("problem_id") for row in rows],
        }

    payload = json.dumps(runbook, indent=2, sort_keys=True)
    if config.DEMO_MODE:
        config.LOCAL_STATE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            (config.LOCAL_STATE_DIR / "learned_patterns.json").write_text(payload, encoding="utf-8")
        except OSError:
            pass
    else:
        if storage is None:
            raise RuntimeError("google-cloud-storage is required outside demo mode")
        client = storage.Client()
        client.bucket(config.INCIDENT_BUCKET).blob(RUNBOOK_KEY).upload_from_string(payload, content_type="application/json")
    return runbook


def get_runbook() -> dict[str, Any]:
    local_path = config.LOCAL_STATE_DIR / "learned_patterns.json"
    if config.DEMO_MODE:
        if local_path.exists():
            return json.loads(local_path.read_text(encoding="utf-8"))
        return update_runbook()

    if storage is None:
        raise RuntimeError("google-cloud-storage is required outside demo mode")
    client = storage.Client()
    blob = client.bucket(config.INCIDENT_BUCKET).blob(RUNBOOK_KEY)
    if not blob.exists():
        return update_runbook()
    return json.loads(blob.download_as_text())
