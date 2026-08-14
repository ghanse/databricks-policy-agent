from types import SimpleNamespace

from policy_agent.scan.resources import (
    classify_principal,
    scan_clusters,
    scan_jobs,
    scan_serving_endpoints,
    scan_sql_warehouses,
)


class _FakeService:
    def __init__(self, items, list_kwargs_ok=True):
        self._items = items
        self._list_kwargs_ok = list_kwargs_ok

    def list(self, **_kwargs):
        return list(self._items)


def _ws(**services):
    return SimpleNamespace(**services)


def test_classify_principal_distinguishes_kinds():
    assert classify_principal("11111111-2222-3333-4444-555555555555") == "service_principal"
    assert classify_principal("alice@example.com") == "user"
    assert classify_principal("data-eng-group") == "unknown"
    assert classify_principal(None) == "unknown"


def test_scan_jobs_uses_run_as_service_principal_and_tags():
    job = SimpleNamespace(
        job_id=42,
        created_time=1_700_000_000_000,
        creator_user_name="alice@example.com",
        settings=SimpleNamespace(
            name="prod_etl",
            tags={"cost_center": "1"},
            max_concurrent_runs=1,
            timeout_seconds=3600,
            format=SimpleNamespace(value="MULTI_TASK"),
            run_as=SimpleNamespace(
                service_principal_name="11111111-2222-3333-4444-555555555555",
                user_name=None,
            ),
            schedule=SimpleNamespace(pause_status=SimpleNamespace(value="UNPAUSED")),
            email_notifications=SimpleNamespace(on_failure=["oncall@example.com"]),
        ),
    )
    (snapshot,) = scan_jobs(_ws(jobs=_FakeService([job])))
    attrs = snapshot.attributes
    assert attrs["name"] == "prod_etl"
    assert attrs["owner_type"] == "service_principal"
    assert attrs["tags"] == {"cost_center": "1"}
    assert attrs["created_time"] == 1_700_000_000
    assert attrs["schedule_pause_status"] == "UNPAUSED"
    assert attrs["has_email_notifications"] is True
    assert attrs["format"] == "MULTI_TASK"


def test_scan_clusters_classifies_creator_and_normalizes_enum():
    cluster = SimpleNamespace(
        cluster_id="c1",
        cluster_name="scratch",
        creator_user_name="bob@example.com",
        custom_tags={"team": "ml"},
        start_time=1_700_000_000_000,
        cluster_source=SimpleNamespace(value="UI"),
        autotermination_minutes=0,
        spark_version="14.3",
        node_type_id="i3.xlarge",
        num_workers=2,
        data_security_mode=SimpleNamespace(value="SINGLE_USER"),
        single_user_name="bob@example.com",
    )
    (snapshot,) = scan_clusters(_ws(clusters=_FakeService([cluster])))
    attrs = snapshot.attributes
    assert attrs["owner_type"] == "user"
    assert attrs["cluster_source"] == "UI"
    assert attrs["autotermination_minutes"] == 0
    assert attrs["tags"] == {"team": "ml"}


def test_scan_warehouses_normalizes_endpoint_tag_pairs():
    warehouse = SimpleNamespace(
        id="w1",
        name="serverless",
        creator_name="carol@example.com",
        tags=SimpleNamespace(
            custom_tags=[SimpleNamespace(key="env", value="prod")],
        ),
        warehouse_type=SimpleNamespace(value="PRO"),
        cluster_size="Small",
        auto_stop_mins=10,
        enable_serverless_compute=True,
        min_num_clusters=1,
        max_num_clusters=1,
    )
    (snapshot,) = scan_sql_warehouses(_ws(warehouses=_FakeService([warehouse])))
    attrs = snapshot.attributes
    assert attrs["tags"] == {"env": "prod"}
    assert attrs["auto_stop_minutes"] == 10
    assert attrs["warehouse_type"] == "PRO"


def test_scan_serving_endpoints_reads_nested_state():
    endpoint = SimpleNamespace(
        id="e1",
        name="fraud-model",
        creator="dana@example.com",
        creation_timestamp=1_700_000_000_000,
        tags=[SimpleNamespace(key="team", value="risk")],
        state=SimpleNamespace(ready=SimpleNamespace(value="READY")),
        endpoint_type=None,
        budget_policy_id=None,
        route_optimized=False,
    )
    (snapshot,) = scan_serving_endpoints(_ws(serving_endpoints=_FakeService([endpoint])))
    attrs = snapshot.attributes
    assert attrs["endpoint_state"] == "READY"
    assert attrs["tags"] == {"team": "risk"}
    assert attrs["route_optimized"] is False
