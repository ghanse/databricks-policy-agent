from types import SimpleNamespace

from policy_agent.policy.model import ResourceType
from policy_agent.scan.resources import (
    classify_principal,
    scan_catalogs,
    scan_clusters,
    scan_external_locations,
    scan_jobs,
    scan_registered_models,
    scan_schemas,
    scan_secret_scopes,
    scan_serving_endpoints,
    scan_sql_warehouses,
    scan_volumes,
)


class _FakeService:
    def __init__(self, items, list_kwargs_ok=True):
        self._items = items
        self._list_kwargs_ok = list_kwargs_ok
        self.list_kwargs = None

    def list(self, **kwargs):
        self.list_kwargs = kwargs
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


def _job_with_tasks(tasks):
    return SimpleNamespace(
        job_id=1,
        created_time=None,
        creator_user_name="alice@example.com",
        settings=SimpleNamespace(name="prod_etl", tasks=tasks),
    )


def test_scan_jobs_detects_retry_policy_across_tasks():
    retried = _job_with_tasks([SimpleNamespace(max_retries=3), SimpleNamespace(max_retries=-1)])
    partial = _job_with_tasks([SimpleNamespace(max_retries=3), SimpleNamespace(max_retries=0)])
    invalid = _job_with_tasks([SimpleNamespace(max_retries=3), SimpleNamespace(max_retries=-2)])
    (retried_snapshot,) = scan_jobs(_ws(jobs=_FakeService([retried])))
    (partial_snapshot,) = scan_jobs(_ws(jobs=_FakeService([partial])))
    (invalid_snapshot,) = scan_jobs(_ws(jobs=_FakeService([invalid])))
    assert retried_snapshot.attributes["has_retry_policy"] is True
    assert partial_snapshot.attributes["has_retry_policy"] is False
    assert invalid_snapshot.attributes["has_retry_policy"] is False


def test_scan_jobs_detects_serverless_compute():
    serverless = _job_with_tasks([SimpleNamespace(environment_key="default")])
    classic = _job_with_tasks([SimpleNamespace(existing_cluster_id="c-1")])
    (serverless_snapshot,) = scan_jobs(_ws(jobs=_FakeService([serverless])))
    (classic_snapshot,) = scan_jobs(_ws(jobs=_FakeService([classic])))
    assert serverless_snapshot.attributes["uses_serverless_compute"] is True
    assert classic_snapshot.attributes["uses_serverless_compute"] is False


def test_scan_jobs_skips_task_expansion_when_disabled():
    job = _job_with_tasks([SimpleNamespace(max_retries=3)])
    jobs = _FakeService([job])
    (snapshot,) = scan_jobs(_ws(jobs=jobs), expand_tasks=False)
    # Don't ask the API for tasks, and report task-derived attributes as unknown rather than a
    # value guessed from tasks that were never fetched.
    assert jobs.list_kwargs == {"expand_tasks": False}
    assert snapshot.attributes["has_retry_policy"] is None
    assert snapshot.attributes["uses_serverless_compute"] is None
    # Non-task attributes are still populated.
    assert snapshot.attributes["name"] == "prod_etl"


def test_scan_jobs_expands_tasks_by_default():
    jobs = _FakeService([_job_with_tasks([SimpleNamespace(max_retries=3)])])
    scan_jobs(_ws(jobs=jobs))
    assert jobs.list_kwargs == {"expand_tasks": True}


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


class _FakeSecrets:
    def __init__(self, scopes):
        self._scopes = scopes

    def list_scopes(self):
        return list(self._scopes)


def test_scan_catalogs_maps_owner_type_and_created_time():
    catalog = SimpleNamespace(
        name="main",
        owner="data-eng",
        created_at=1_700_000_000_000,
        comment="prod catalog",
        catalog_type=SimpleNamespace(value="MANAGED_CATALOG"),
        isolation_mode=SimpleNamespace(value="ISOLATED"),
        storage_root="s3://bucket/main",
    )
    (snapshot,) = scan_catalogs(_ws(catalogs=_FakeService([catalog])))
    attrs = snapshot.attributes
    assert snapshot.resource_type is ResourceType.CATALOG
    assert attrs["name"] == "main"
    assert attrs["owner"] == "data-eng"
    assert attrs["owner_type"] == "unknown"  # a group name is neither user nor SP
    assert attrs["catalog_type"] == "MANAGED_CATALOG"
    assert attrs["isolation_mode"] == "ISOLATED"
    assert attrs["created_time"] == 1_700_000_000
    assert "tags" not in attrs  # catalogs do not advertise tags


def test_scan_schemas_iterates_catalogs():
    catalog = SimpleNamespace(name="main")
    schema = SimpleNamespace(
        name="analytics",
        full_name="main.analytics",
        owner="alice@example.com",
        created_at=None,
        comment="gold",
    )
    ws = _ws(catalogs=_FakeService([catalog]), schemas=_FakeService([schema]))
    (snapshot,) = scan_schemas(ws)
    attrs = snapshot.attributes
    assert snapshot.resource_type is ResourceType.SCHEMA
    assert attrs["id"] == "main.analytics"
    assert attrs["catalog_name"] == "main"
    assert attrs["owner_type"] == "user"


def test_scan_volumes_iterates_catalogs_and_schemas():
    catalog = SimpleNamespace(name="main")
    schema = SimpleNamespace(name="analytics")
    volume = SimpleNamespace(
        name="landing",
        full_name="main.analytics.landing",
        owner="data-eng",
        created_at=None,
        comment=None,
        volume_type=SimpleNamespace(value="MANAGED"),
    )
    ws = _ws(
        catalogs=_FakeService([catalog]),
        schemas=_FakeService([schema]),
        volumes=_FakeService([volume]),
    )
    (snapshot,) = scan_volumes(ws)
    attrs = snapshot.attributes
    assert snapshot.resource_type is ResourceType.VOLUME
    assert attrs["id"] == "main.analytics.landing"
    assert attrs["catalog_name"] == "main"
    assert attrs["schema_name"] == "analytics"
    assert attrs["volume_type"] == "MANAGED"


def test_scan_registered_models_maps_names():
    model = SimpleNamespace(
        name="churn",
        full_name="main.ml.churn",
        owner="11111111-2222-3333-4444-555555555555",
        created_at=None,
        comment=None,
        catalog_name="main",
        schema_name="ml",
    )
    (snapshot,) = scan_registered_models(_ws(registered_models=_FakeService([model])))
    attrs = snapshot.attributes
    assert snapshot.resource_type is ResourceType.REGISTERED_MODEL
    assert attrs["id"] == "main.ml.churn"
    assert attrs["owner_type"] == "service_principal"
    assert attrs["schema_name"] == "ml"


def test_scan_external_locations_maps_url_and_read_only():
    location = SimpleNamespace(
        name="raw-landing",
        owner="data-eng",
        created_at=None,
        comment=None,
        url="s3://bucket/raw",
        credential_name="raw-cred",
        read_only=True,
        isolation_mode=SimpleNamespace(value="ISOLATED"),
    )
    (snapshot,) = scan_external_locations(_ws(external_locations=_FakeService([location])))
    attrs = snapshot.attributes
    assert snapshot.resource_type is ResourceType.EXTERNAL_LOCATION
    assert attrs["url"] == "s3://bucket/raw"
    assert attrs["credential_name"] == "raw-cred"
    assert attrs["read_only"] is True
    assert attrs["isolation_mode"] == "ISOLATED"


def test_scan_secret_scopes_maps_backend_type():
    scope = SimpleNamespace(name="prod-secrets", backend_type=SimpleNamespace(value="DATABRICKS"))
    (snapshot,) = scan_secret_scopes(_ws(secrets=_FakeSecrets([scope])))
    attrs = snapshot.attributes
    assert snapshot.resource_type is ResourceType.SECRET_SCOPE
    assert attrs["name"] == "prod-secrets"
    assert attrs["backend_type"] == "DATABRICKS"
    assert "owner" not in attrs and "tags" not in attrs
