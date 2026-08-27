"""Integration tests that scan real workspace resources created by pytester fixtures."""

import pytest

from policy_agent.policy import allow, leaf
from policy_agent.policy.model import ResourceType
from policy_agent.scan import run_scan
from policy_agent.scan.engine import collect_snapshots


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
def test_scan_catalogs_includes_created_catalog(ws, make_catalog):
    """A newly created catalog appears in the catalog scan."""
    catalog = make_catalog()
    snapshots = collect_snapshots(ws, [ResourceType.CATALOG])[ResourceType.CATALOG]
    assert catalog.name in {s.resource_id for s in snapshots}


@pytest.mark.integration
def test_scan_schemas_includes_created_schema(ws, make_catalog, make_schema):
    """A newly created schema appears in the schema scan, keyed by its full name."""
    catalog = make_catalog()
    schema = make_schema(catalog_name=catalog.name)
    snapshots = collect_snapshots(ws, [ResourceType.SCHEMA])[ResourceType.SCHEMA]
    assert schema.full_name in {s.resource_id for s in snapshots}


@pytest.mark.integration
def test_scan_volumes_includes_created_volume(ws, make_volume):
    """A newly created volume appears in the volume scan, keyed by its full name."""
    volume = make_volume()
    snapshots = collect_snapshots(ws, [ResourceType.VOLUME])[ResourceType.VOLUME]
    assert volume.full_name in {s.resource_id for s in snapshots}


@pytest.mark.integration
def test_scan_secret_scopes_includes_created_scope(ws, make_secret_scope):
    """A newly created secret scope appears in the secret-scope scan."""
    scope = make_secret_scope()
    snapshots = collect_snapshots(ws, [ResourceType.SECRET_SCOPE])[ResourceType.SECRET_SCOPE]
    assert scope in {s.resource_id for s in snapshots}


@pytest.mark.integration
def test_scan_registered_models_includes_created_model(ws, make_catalog, make_schema, make_random):
    """A registered model appears in the scan. No pytester fixture exists, so create/clean up here."""
    catalog = make_catalog()
    schema = make_schema(catalog_name=catalog.name)
    name = f"model_{make_random(6).lower()}"
    model = ws.registered_models.create(
        catalog_name=catalog.name, schema_name=schema.name, name=name
    )
    try:
        snapshots = collect_snapshots(ws, [ResourceType.REGISTERED_MODEL])[
            ResourceType.REGISTERED_MODEL
        ]
        assert model.full_name in {s.resource_id for s in snapshots}
    finally:
        ws.registered_models.delete(full_name=model.full_name)


@pytest.mark.integration
def test_scan_external_locations_maps_live_shape(ws, env_or_skip):
    """External locations have no pytester fixture (they need real cloud storage), so this
    exercises the live list shape and skips when the metastore has none."""
    env_or_skip("DATABRICKS_HOST")
    snapshots = collect_snapshots(ws, [ResourceType.EXTERNAL_LOCATION])[
        ResourceType.EXTERNAL_LOCATION
    ]
    if not snapshots:
        pytest.skip("no external locations in the metastore to evaluate")
    assert all("url" in s.attributes for s in snapshots)


@pytest.mark.integration
def test_scan_evaluates_pipeline_naming_policy(
    ws, make_catalog, make_schema, make_pipeline, make_random
):
    """A pipeline created with a conforming name is compliant with a naming policy."""
    suffix = make_random(6).lower()
    catalog = make_catalog(name="test")
    schema = make_schema(catalog_name=catalog.name)
    pipeline = make_pipeline(name=f"dev_{suffix}", catalog=catalog.name, schema=schema.name)

    naming = allow(
        "pipeline-naming",
        ResourceType.PIPELINE,
        leaf("name", "matches_regex", r"^dev_[a-z0-9]+$"),
    )
    result = run_scan(ws, [naming], [ResourceType.PIPELINE])

    compliant_ids = {f.resource_id for f in result.findings if f.compliant}
    assert str(pipeline.pipeline_id) in compliant_ids


@pytest.mark.integration
def test_scan_genie_spaces_maps_live_shape(ws, env_or_skip):
    """Scanning real Genie spaces produces well-formed snapshots (a schema-drift guard)."""
    env_or_skip("DATABRICKS_HOST")
    snapshots = collect_snapshots(ws, [ResourceType.GENIE_SPACE])[ResourceType.GENIE_SPACE]
    if not snapshots:
        pytest.skip("no Genie spaces in the workspace to evaluate")

    assert all(s.resource_id for s in snapshots)
    assert all(s.name for s in snapshots)
    assert all(isinstance(s.attributes["has_description"], bool) for s in snapshots)

    documented = allow(
        "genie-space-documented",
        ResourceType.GENIE_SPACE,
        leaf("has_description", "equals", True),
    )
    result = run_scan(ws, [documented], [ResourceType.GENIE_SPACE])
    if result.summary().evaluated == 0:
        pytest.skip("Genie spaces disappeared between fetches; nothing to evaluate")
    # Every evaluated space is either compliant or a violation, with no double counting.
    summary = result.summary()
    assert summary.evaluated == summary.compliant + summary.violations
