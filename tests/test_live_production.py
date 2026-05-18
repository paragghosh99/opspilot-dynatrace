from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

import pytest


BASE_URL = os.getenv("OPSPILOT_LIVE_BASE_URL", "https://opspilot-440723503018.us-central1.run.app").rstrip("/")


def _json_request(path: str, method: str = "GET", timeout: int = 45) -> dict:
    request = urllib.request.Request(f"{BASE_URL}{path}", method=method)
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            assert response.status < 500
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        pytest.fail(f"{method} {path} failed with HTTP {exc.code}: {body}")


@pytest.mark.live_safe
@pytest.mark.parametrize(
    ("path", "key"),
    [
        ("/health", "status"),
        ("/api/problems", "problems"),
        ("/api/incidents", "incidents"),
        ("/api/mttr", "points"),
        ("/api/runbook", "runbook"),
    ],
)
def test_live_safe_json_endpoints(path: str, key: str):
    payload = _json_request(path)

    assert key in payload


@pytest.mark.live_safe
def test_live_openapi_contains_expected_routes():
    payload = _json_request("/openapi.json")

    for route in ["/health", "/api/problems", "/api/incidents", "/api/mttr", "/api/runbook", "/poll"]:
        assert route in payload["paths"]


@pytest.mark.live_safe
def test_live_dynatrace_problem_shape_if_present():
    payload = _json_request("/api/problems")

    for problem in payload["problems"]:
        assert problem["problemId"]
        assert problem["title"]
        assert problem["severityLevel"]
        assert isinstance(problem.get("entityNames", []), list)


@pytest.mark.live_expensive
def test_live_pipeline_poll_opt_in():
    if os.getenv("ENABLE_EXPENSIVE_LIVE_TESTS", "false").lower() != "true":
        pytest.skip("Set ENABLE_EXPENSIVE_LIVE_TESTS=true to run the live /poll pipeline.")

    max_runs = int(os.getenv("MAX_LIVE_PIPELINE_TESTS", "1"))
    cooldown = int(os.getenv("LIVE_PIPELINE_COOLDOWN_SECONDS", "30"))
    assert 1 <= max_runs <= 3

    problems = _json_request("/api/problems")["problems"]
    if not problems:
        pytest.skip("No active Dynatrace incidents; skipping expensive live pipeline test.")

    for run in range(max_runs):
        payload = _json_request("/poll", method="POST", timeout=120)
        assert "new_problems" in payload
        assert "handled" in payload
        if run < max_runs - 1:
            time.sleep(cooldown)
