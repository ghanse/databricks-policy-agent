"""Tests for the app-tree build helpers (scripts/build_app.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

_BUILD_APP = Path(__file__).resolve().parent.parent / "scripts" / "build_app.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_app", _BUILD_APP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_env_block_escapes_quotes_and_backslashes(monkeypatch):
    build_app = _load_module()
    # A value with a double quote and a backslash would break a naive value: "..." line.
    monkeypatch.setenv("POLICY_AGENT_CATALOG", "main")
    monkeypatch.setenv("POLICY_AGENT_TAGS", 'team="a\\b",x=y')
    for unused in (
        "POLICY_AGENT_STORAGE_BACKEND",
        "POLICY_AGENT_SCHEMA",
        "POLICY_AGENT_NOTIFICATION_EMAILS",
        "POLICY_AGENT_NOTIFICATION_WEBHOOK",
        "POLICY_AGENT_LAKEBASE_URL",
    ):
        monkeypatch.delenv(unused, raising=False)

    parsed = yaml.safe_load(build_app._env_block())
    env = {item["name"]: item for item in parsed["env"]}
    assert env["POLICY_AGENT_TAGS"]["value"] == 'team="a\\b",x=y'
    assert env["POLICY_AGENT_CATALOG"]["value"] == "main"
    # The warehouse id is always present and resolved from the app resource.
    assert env["POLICY_AGENT_WAREHOUSE_ID"]["valueFrom"] == "policy-agent-warehouse"
