import json

import pytest

from agent import config


@pytest.fixture(autouse=True)
def force_demo_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(config, "LOCAL_STATE_DIR", tmp_path / ".opspilot")


@pytest.fixture
def sample_problem():
    return json.loads(config.FIXTURE_PROBLEM.read_text(encoding="utf-8"))
