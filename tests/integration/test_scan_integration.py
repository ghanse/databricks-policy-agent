"""Integration tests that scan real workspace resources created by pytester fixtures."""

import pytest

from policy_agent.policy import allow, leaf
from policy_agent.policy.model import ResourceType
from policy_agent.scan import run_scan


@pytest.mark.integration
def test_scan_flags_job_that_breaks_naming_convention(ws, make_job, make_random):
    """A job whose name breaks the required convention is reported as a violation."""
    suffix = make_random(6).lower()
    job = make_job(name=f"invalid {suffix}")

    policy = allow(
        "job-naming-convention",
        ResourceType.JOB,
        leaf("name", "matches_regex", r"^(prod|stg|dev)_[a-z0-9_]+$"),
    )
    result = run_scan(ws, [policy], [ResourceType.JOB])

    violating_ids = {finding.resource_id for finding in result.violations}
    assert str(job.job_id) in violating_ids


@pytest.mark.integration
def test_scan_reports_compliance_for_conforming_job(ws, make_job, make_random):
    """A job that satisfies the policy is evaluated as compliant, not a violation."""
    suffix = make_random(6).lower()
    job = make_job(name=f"dev_{suffix}")

    policy = allow(
        "job-naming-convention",
        ResourceType.JOB,
        leaf("name", "matches_regex", r"^(prod|stg|dev)_[a-z0-9_]+$"),
    )
    result = run_scan(ws, [policy], [ResourceType.JOB])

    compliant_ids = {f.resource_id for f in result.findings if f.compliant}
    violating_ids = {f.resource_id for f in result.violations}
    assert str(job.job_id) in compliant_ids
    assert str(job.job_id) not in violating_ids
