"""Integration test for the enforcement gate against a real resolved bundle.

Unlike the scan tests, the gate never touches live workspace objects — it evaluates the
config that ``databricks bundle validate --output json`` produces. The value of running this
against a workspace is to confirm our parser handles the *real* resolved-JSON shape (the risk a
hand-authored fixture cannot cover). Requires the ``databricks`` CLI and workspace auth.
"""

from pathlib import Path

import pytest

from policy_agent.enforce import load_bundle_config, run_gate, snapshot_bundle
from policy_agent.policy import allow, leaf
from policy_agent.policy.model import EnforcementLevel, ResourceType

BUNDLE_DIR = Path(__file__).parent / "sample_bundle"


@pytest.mark.integration
def test_gate_over_real_resolved_bundle(env_or_skip):
    """Resolve the sample bundle for real and gate its declared jobs."""
    env_or_skip("DATABRICKS_HOST")

    config = load_bundle_config(BUNDLE_DIR, target="dev")
    jobs = {
        snapshot.resource_id: snapshot
        for snapshot in snapshot_bundle(config)
        if snapshot.resource_type is ResourceType.JOB
    }
    assert {"compliant_job", "violating_job"} <= set(jobs)
    assert jobs["compliant_job"].attributes["has_email_notifications"] is True
    assert jobs["violating_job"].attributes["has_email_notifications"] is False

    must_be_tagged = allow(
        "jobs-must-be-tagged",
        ResourceType.JOB,
        leaf("tags", "has_tag", "team"),
        enforcement_level="hard",
    )
    result = run_gate([must_be_tagged], list(jobs.values()), fail_on=EnforcementLevel.HARD)

    blocking_ids = {finding.resource_id for finding in result.blocking}
    assert "violating_job" in blocking_ids
    assert "compliant_job" not in blocking_ids
    assert result.blocked
