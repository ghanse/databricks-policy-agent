"""Tests for the deployable-tree writers in the build script.

These cover the two files the Databricks App runtime reads — ``app.yaml`` and
``requirements.txt`` — without running the wheel build itself.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_BUILD_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_app.py"


def _load_build_module():
    spec = importlib.util.spec_from_file_location("mcp_build_app", _BUILD_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_app_yaml_launches_the_server(tmp_path, monkeypatch):
    build = _load_build_module()
    monkeypatch.setattr(build, "BUILD_DIR", tmp_path)
    build._write_app_yaml()
    app_yaml = (tmp_path / "app.yaml").read_text(encoding="utf-8")
    # The Databricks App runtime runs this command; it must launch the MCP server module.
    assert 'command: ["python", "-m", "policy_agent_mcp.server"]' in app_yaml


def test_requirements_pin_the_wheel_and_mcp(tmp_path, monkeypatch):
    build = _load_build_module()
    monkeypatch.setattr(build, "BUILD_DIR", tmp_path)
    build._write_requirements("databricks_policy_agent-0.1.0-py3-none-any.whl")
    requirements = (tmp_path / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert "databricks_policy_agent-0.1.0-py3-none-any.whl" in requirements
    assert any(line.startswith("mcp>=") for line in requirements)
