"""Offline coverage of the enforce CLI and the resolved-bundle parser.

These use a committed golden ``resolved_bundle.json`` (a hand-authored capture of the shape
``databricks bundle validate --output json`` emits) so they need no workspace or CLI. The
live integration test in ``tests/integration`` is the source of truth for the real shape.
"""

import os
import subprocess
import sys
from pathlib import Path

from policy_agent.enforce import load_bundle_config, snapshot_bundle
from policy_agent.policy.model import ResourceType

_REPO_ROOT = Path(__file__).parents[2]
GOLDEN = _REPO_ROOT / "tests" / "fixtures" / "resolved_bundle.json"

_HARD_TAGGED = """
policy: jobs-tagged
description: Jobs must carry a team tag.
resource_type: job
effect: allow
enforcement_level: hard
rule:
  all:
    - { attribute: tags, operator: has_tag, value: team }
remediation: Add a team tag to the job.
"""

_ADVISORY_TAGGED = _HARD_TAGGED.replace("enforcement_level: hard", "enforcement_level: advisory")


def test_snapshot_parses_resolved_bundle_shape():
    by_id = {s.resource_id: s for s in snapshot_bundle(load_bundle_config(GOLDEN))}
    assert set(by_id) == {"compliant_job", "violating_job"}
    assert by_id["compliant_job"].resource_type is ResourceType.JOB
    assert by_id["compliant_job"].attributes["tags"] == {"team": "data-platform"}
    assert by_id["compliant_job"].attributes["has_email_notifications"] is True
    assert by_id["violating_job"].attributes["tags"] == {}
    assert by_id["violating_job"].attributes["has_email_notifications"] is False


def _run_enforce(*args: str):
    env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "policy_agent.cli", "enforce", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _policy_file(tmp_path: Path, body: str) -> str:
    path = tmp_path / "policies.yaml"
    path.write_text(body, encoding="utf-8")
    return str(path)


def test_cli_blocks_on_hard_violation(tmp_path):
    result = _run_enforce(
        "--bundle",
        str(GOLDEN),
        "--policies",
        _policy_file(tmp_path, _HARD_TAGGED),
        "--fail-on",
        "hard",
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "violating_job" in result.stdout


def test_cli_passes_when_only_advisory(tmp_path):
    result = _run_enforce(
        "--bundle",
        str(GOLDEN),
        "--policies",
        _policy_file(tmp_path, _ADVISORY_TAGGED),
        "--fail-on",
        "hard",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cli_rejects_override_without_reason(tmp_path):
    result = _run_enforce(
        "--bundle",
        str(GOLDEN),
        "--policies",
        _policy_file(tmp_path, _HARD_TAGGED),
        "--override",
        "jobs-tagged",
    )
    assert result.returncode == 2
