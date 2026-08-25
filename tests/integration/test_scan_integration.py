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


@pytest.mark.integration
def test_scan_evaluates_cluster_autotermination_policy(ws, make_cluster):
    """A cluster is compliant with a lenient auto-termination limit and violates a strict one."""
    cluster = make_cluster(single_node=True, autotermination_minutes=10)

    within_limit = allow(
        "cluster-auto-terminates",
        ResourceType.CLUSTER,
        leaf("autotermination_minutes", "ttl_within", 60),
    )
    compliant = run_scan(ws, [within_limit], [ResourceType.CLUSTER])
    compliant_ids = {f.resource_id for f in compliant.findings if f.compliant}
    assert str(cluster.cluster_id) in compliant_ids

    strict_limit = allow(
        "cluster-auto-terminates-fast",
        ResourceType.CLUSTER,
        leaf("autotermination_minutes", "ttl_within", 5),
    )
    strict = run_scan(ws, [strict_limit], [ResourceType.CLUSTER])
    violating_ids = {f.resource_id for f in strict.violations}
    assert str(cluster.cluster_id) in violating_ids


@pytest.mark.integration
def test_scan_evaluates_warehouse_size_policy(ws, make_warehouse):
    """A warehouse is compliant with an allowed-size policy and violates a stricter one."""
    warehouse = make_warehouse(cluster_size="Small")

    approved_sizes = allow(
        "warehouse-approved-size",
        ResourceType.SQL_WAREHOUSE,
        leaf("cluster_size", "in", ["2X-Small", "X-Small", "Small", "Medium"]),
    )
    compliant = run_scan(ws, [approved_sizes], [ResourceType.SQL_WAREHOUSE])
    compliant_ids = {f.resource_id for f in compliant.findings if f.compliant}
    assert str(warehouse.id) in compliant_ids

    large_only = allow(
        "warehouse-large-only",
        ResourceType.SQL_WAREHOUSE,
        leaf("cluster_size", "equals", "Large"),
    )
    strict = run_scan(ws, [large_only], [ResourceType.SQL_WAREHOUSE])
    violating_ids = {f.resource_id for f in strict.violations}
    assert str(warehouse.id) in violating_ids


@pytest.mark.integration
def test_scan_reports_tagged_job_compliant_with_not_empty(ws, make_job, make_random):
    """A job that carries tags satisfies a 'must be tagged' (not_empty) policy."""
    suffix = make_random(6).lower()
    job = make_job(name=f"dev_{suffix}", tags={"team": f"platform_{suffix}"})

    policy = allow(
        "jobs-must-be-tagged",
        ResourceType.JOB,
        leaf("tags", "not_empty"),
    )
    result = run_scan(ws, [policy], [ResourceType.JOB])

    compliant_ids = {f.resource_id for f in result.findings if f.compliant}
    violating_ids = {f.resource_id for f in result.violations}
    assert str(job.job_id) in compliant_ids
    assert str(job.job_id) not in violating_ids


@pytest.mark.integration
def test_scan_flags_job_without_retry_policy_or_serverless_compute(ws, make_job, make_random):
    """A default job (classic compute, no task retries) violates retry and serverless policies."""
    suffix = make_random(6).lower()
    job = make_job(name=f"dev_{suffix}")

    must_retry = allow(
        "jobs-must-have-retry-policy",
        ResourceType.JOB,
        leaf("has_retry_policy", "equals", True),
    )
    retry_result = run_scan(ws, [must_retry], [ResourceType.JOB])
    assert str(job.job_id) in {f.resource_id for f in retry_result.violations}

    must_be_serverless = allow(
        "jobs-should-use-serverless-compute",
        ResourceType.JOB,
        leaf("uses_serverless_compute", "equals", True),
    )
    serverless_result = run_scan(ws, [must_be_serverless], [ResourceType.JOB])
    assert str(job.job_id) in {f.resource_id for f in serverless_result.violations}


@pytest.mark.integration
def test_scan_evaluates_pipeline_naming_policy(ws, make_pipeline, make_random):
    """A pipeline created with a conforming name is compliant with a naming policy."""
    suffix = make_random(6).lower()
    pipeline = make_pipeline(name=f"dev_{suffix}")

    naming = allow(
        "pipeline-naming",
        ResourceType.PIPELINE,
        leaf("name", "matches_regex", r"^dev_[a-z0-9]+$"),
    )
    result = run_scan(ws, [naming], [ResourceType.PIPELINE])

    compliant_ids = {f.resource_id for f in result.findings if f.compliant}
    assert str(pipeline.pipeline_id) in compliant_ids
