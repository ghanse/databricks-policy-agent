from types import SimpleNamespace

from policy_agent.policy import deny, leaf
from policy_agent.policy.model import ResourceType
from policy_agent.scan.engine import run_scan
from policy_agent.scan.registry import supported_resource_types


class _Service:
    def __init__(self, items):
        self._items = items

    def list(self, **_kwargs):
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


def test_supported_resource_types_match_registry():
    assert set(supported_resource_types()) == {
        ResourceType.JOB,
        ResourceType.CLUSTER,
        ResourceType.SQL_WAREHOUSE,
        ResourceType.APP,
        ResourceType.SERVING_ENDPOINT,
    }


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


def test_run_scan_respects_resource_type_restriction():
    policy = deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    ws = _ws_with_clusters([_cluster("c1", "alice@example.com")])

    result = run_scan(ws, [policy], resource_types=[ResourceType.JOB])

    assert result.findings == ()
