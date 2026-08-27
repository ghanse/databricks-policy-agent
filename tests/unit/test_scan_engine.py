from types import SimpleNamespace

import pytest

from policy_agent.errors import UnsupportedResourceError
from policy_agent.policy import allow, deny, leaf
from policy_agent.policy.model import ResourceType
from policy_agent.scan import registry
from policy_agent.scan.engine import run_scan
from policy_agent.scan.registry import scanner_for, supported_resource_types


class _Service:
    def __init__(self, items):
        self._items = items
        self.list_kwargs = None

    def list(self, **kwargs):
        self.list_kwargs = kwargs
        return list(self._items)


def _cluster(cluster_id, creator):
    return SimpleNamespace(
        cluster_id=cluster_id,
        cluster_name=cluster_id,
        creator_user_name=creator,
        custom_tags={},
        start_time=None,
        cluster_source=SimpleNamespace(value="UI"),
        autotermination_minutes=0,
        spark_version="14.3",
        node_type_id="i3.xlarge",
        num_workers=1,
        data_security_mode=None,
        single_user_name=None,
    )


def _ws_with_clusters(clusters):
    empty = _Service([])
    return SimpleNamespace(
        jobs=empty,
        clusters=_Service(clusters),
        warehouses=empty,
        apps=empty,
        serving_endpoints=empty,
    )


def _job(job_id, name):
    return SimpleNamespace(
        job_id=job_id,
        created_time=None,
        creator_user_name="alice@example.com",
        settings=SimpleNamespace(name=name, tags={}, tasks=[SimpleNamespace(max_retries=3)]),
    )


def _ws_with_jobs(jobs_service):
    empty = _Service([])
    return SimpleNamespace(
        jobs=jobs_service,
        clusters=empty,
        warehouses=empty,
        apps=empty,
        serving_endpoints=empty,
    )


def test_supported_resource_types_match_registry():
    assert set(supported_resource_types()) == {
        ResourceType.JOB,
        ResourceType.CLUSTER,
        ResourceType.SQL_WAREHOUSE,
        ResourceType.APP,
        ResourceType.SERVING_ENDPOINT,
        ResourceType.CATALOG,
        ResourceType.SCHEMA,
        ResourceType.VOLUME,
        ResourceType.REGISTERED_MODEL,
        ResourceType.EXTERNAL_LOCATION,
        ResourceType.SECRET_SCOPE,
        ResourceType.PIPELINE,
        ResourceType.GENIE_SPACE,
        ResourceType.DATABASE_INSTANCE,
    }
    # Quality monitors are enforce-only (no list API), so they are not scannable.
    assert ResourceType.QUALITY_MONITOR not in set(supported_resource_types())


def test_run_scan_skips_enforce_only_types():
    # A quality-monitor policy is valid and can be gated from a bundle, but a live scan skips it
    # because there is no list API — so no scanner is called and no findings are produced.
    policy = allow("qm-scheduled", "quality_monitor", leaf("has_schedule", "equals", True))
    result = run_scan(SimpleNamespace(), [policy])
    assert result.findings == ()
    assert result.resource_types == ()


def test_scanner_for_unregistered_type_raises_unsupported_resource(monkeypatch):
    monkeypatch.delitem(registry.RESOURCE_SCANNERS, ResourceType.GENIE_SPACE)
    with pytest.raises(UnsupportedResourceError):
        scanner_for(ResourceType.GENIE_SPACE)


def test_run_scan_only_fetches_types_referenced_by_policies(monkeypatch):
    fetched: list[ResourceType] = []
    from policy_agent.scan import engine

    original = engine.scanner_for

    def _tracking_scanner_for(resource_type):
        fetched.append(resource_type)
        return original(resource_type)

    monkeypatch.setattr(engine, "scanner_for", _tracking_scanner_for)

    policy = deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    ws = _ws_with_clusters([_cluster("c1", "alice@example.com")])
    run_scan(ws, [policy])

    assert fetched == [ResourceType.CLUSTER]


def test_run_scan_produces_findings_and_summary():
    policy = deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    ws = _ws_with_clusters(
        [
            _cluster("c1", "alice@example.com"),
            _cluster("c2", "11111111-2222-3333-4444-555555555555"),
        ]
    )

    result = run_scan(ws, [policy])
    summary = result.summary()

    assert summary.evaluated == 2
    assert summary.violations == 1
    assert summary.violations_by_resource_type == {"cluster": 1}
    assert result.violations[0].resource_id == "c1"
    assert 0.0 < summary.compliance_rate < 1.0


def test_run_scan_expands_job_tasks_only_when_a_policy_reads_a_task_attribute():
    # A policy on a non-task attribute should not trigger the expensive task expansion.
    name_only = _Service([_job("j1", "prod_etl")])
    run_scan(_ws_with_jobs(name_only), [deny("named", "job", leaf("name", "equals", "adhoc"))])
    assert name_only.list_kwargs == {"expand_tasks": False}

    # A policy that reads a task-derived attribute must expand tasks.
    task_aware = _Service([_job("j1", "prod_etl")])
    run_scan(
        _ws_with_jobs(task_aware),
        [deny("no-retry", "job", leaf("has_retry_policy", "equals", False))],
    )
    assert task_aware.list_kwargs == {"expand_tasks": True}


def test_run_scan_respects_resource_type_restriction():
    policy = deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    ws = _ws_with_clusters([_cluster("c1", "alice@example.com")])

    result = run_scan(ws, [policy], resource_types=[ResourceType.JOB])

    assert result.findings == ()
