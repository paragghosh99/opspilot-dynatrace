from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

try:
    from google.cloud import storage
except ImportError:
    storage = None

from agent import config


def _local_incident_dir():
    path = config.LOCAL_STATE_DIR / "incidents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_incident(
    problem: dict[str, Any],
    diagnosis: dict[str, Any],
    action_result: dict[str, Any],
    entities: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    record = {
        "problem_id": problem.get("problemId", "unknown"),
        "title": problem.get("title", "Untitled problem"),
        "severity": problem.get("severityLevel", "UNKNOWN"),
        "problem_url": problem.get("problemUrl"),
        "entities": entities or [],
        "root_cause": diagnosis.get("root_cause", "unknown"),
        "diagnosis": diagnosis,
        "action_taken": action_result.get("action"),
        "action_result": action_result,
        "resolved": action_result.get("status") in {"simulated", "published", "called", "queued"},
        "mttr_minutes": problem.get("mttrMinutes", 14),
        "created_at": now.isoformat(),
    }

    key = f"incidents/{now.date().isoformat()}/{record['problem_id']}.json"
    payload = json.dumps(record, indent=2, sort_keys=True)
    if config.DEMO_MODE:
        try:
            (_local_incident_dir() / f"{record['problem_id']}.json").write_text(payload, encoding="utf-8")
        except OSError:
            pass
    else:
        if storage is None:
            raise RuntimeError("google-cloud-storage is required outside demo mode")
        client = storage.Client()
        client.bucket(config.INCIDENT_BUCKET).blob(key).upload_from_string(payload, content_type="application/json")
    return record


def list_incidents() -> list[dict[str, Any]]:
    sample = json.loads(config.FIXTURE_PROBLEM.read_text(encoding="utf-8"))
    if config.DEMO_MODE:
        incident_dir = _local_incident_dir()
        records = [json.loads(path.read_text(encoding="utf-8")) for path in incident_dir.glob("*.json")]
        if records:
            return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)
        return sample["history"]

    if storage is None:
        raise RuntimeError("google-cloud-storage is required outside demo mode")
    client = storage.Client()
    bucket = client.bucket(config.INCIDENT_BUCKET)
    records = [json.loads(blob.download_as_text()) for blob in bucket.list_blobs(prefix="incidents/")]
    if records:
        return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)
    return sample["history"]
