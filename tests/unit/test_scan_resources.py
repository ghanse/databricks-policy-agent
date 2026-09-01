from types import SimpleNamespace

import pytest

from policy_agent.errors import ScanError, UnsupportedResourceError
from policy_agent.policy.model import ResourceType
from policy_agent.scan.resources import (
    classify_principal,
    scan_apps,
    scan_catalogs,
    scan_clusters,
    scan_database_instances,
    scan_external_locations,
    scan_genie_spaces,
    scan_jobs,
    scan_pipelines,
    scan_quality_monitors,
    scan_registered_models,
    scan_schemas,
    scan_secret_scopes,
    scan_serving_endpoints,
    scan_sql_alerts,
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


class _FakeTagAssignments:
    """A fake workspace entity-tag-assignments service keyed by (entity_type, entity_id)."""

    def __init__(self, assignments):
        self._assignments = assignments
        self.calls = []

    def list_tag_assignments(self, entity_type, entity_id, **kwargs):
        self.calls.append((entity_type, entity_id))
        return list(self._assignments.get((entity_type, entity_id), []))


def test_scan_apps_reads_governed_tags():
    app = SimpleNamespace(
        name="sales-app",
        creator="dana@example.com",
        create_time="2026-01-02T03:04:05Z",
        app_status=SimpleNamespace(state=SimpleNamespace(value="RUNNING")),
        compute_status=SimpleNamespace(state=SimpleNamespace(value="ACTIVE")),
        active_deployment=SimpleNamespace(mode=SimpleNamespace(value="SNAPSHOT")),
    )
    tag_service = _FakeTagAssignments(
        {
            ("apps", "sales-app"): [
                SimpleNamespace(tag_key="team", tag_value="sales"),
                SimpleNamespace(tag_key="certified", tag_value=None),
            ]
        }
    )
    ws = _ws(apps=_FakeService([app]), workspace_entity_tag_assignments=tag_service)
    (snapshot,) = scan_apps(ws)
    attrs = snapshot.attributes
    assert attrs["name"] == "sales-app"
    assert attrs["app_status"] == "RUNNING"
    # Tags come from the entity-tag-assignments API, keyed by the app name; a null value is "".
    assert attrs["tags"] == {"team": "sales", "certified": ""}
    assert tag_service.calls == [("apps", "sales-app")]


def test_scan_apps_without_tag_service_reports_untagged():
    app = SimpleNamespace(name="bare-app", creator=None)
    (snapshot,) = scan_apps(_ws(apps=_FakeService([app])))
    assert snapshot.attributes["tags"] == {}


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
    # Catalogs advertise tags; with no UC tag service wired the mapping is empty.
    assert attrs["tags"] == {}


class _FakeUcTagAssignments:
    """A fake UC entity-tag-assignments service keyed by (entity_type, entity_name)."""

    def __init__(self, assignments):
        self._assignments = assignments
        self.calls = []

    def list(self, entity_type, entity_name, **kwargs):
        self.calls.append((entity_type, entity_name))
        return list(self._assignments.get((entity_type, entity_name), []))


def test_scan_catalogs_reads_governed_uc_tags():
    catalog = SimpleNamespace(name="main", owner="data-eng", created_at=None)
    tag_service = _FakeUcTagAssignments(
        {("catalogs", "main"): [SimpleNamespace(tag_key="domain", tag_value="finance")]}
    )
    ws = _ws(catalogs=_FakeService([catalog]), entity_tag_assignments=tag_service)
    (snapshot,) = scan_catalogs(ws)
    # UC tags come from the entity-tag-assignments API, keyed by entity type + fully-qualified name.
    assert snapshot.attributes["tags"] == {"domain": "finance"}
    assert tag_service.calls == [("catalogs", "main")]


def test_scan_volumes_reads_governed_uc_tags_by_full_name():
    catalog = SimpleNamespace(name="main")
    schema = SimpleNamespace(name="gold")
    volume = SimpleNamespace(name="landing", full_name="main.gold.landing", owner="data-eng")
    tag_service = _FakeUcTagAssignments(
        {("volumes", "main.gold.landing"): [SimpleNamespace(tag_key="pii", tag_value="true")]}
    )
    ws = _ws(
        catalogs=_FakeService([catalog]),
        schemas=_FakeService([schema]),
        volumes=_FakeService([volume]),
        entity_tag_assignments=tag_service,
    )
    (snapshot,) = scan_volumes(ws)
    assert snapshot.attributes["tags"] == {"pii": "true"}
    # The volume's fully-qualified name is used as the UC entity name.
    assert tag_service.calls == [("volumes", "main.gold.landing")]


def test_scan_schemas_reads_governed_uc_tags_by_full_name():
    catalog = SimpleNamespace(name="main")
    schema = SimpleNamespace(name="gold", full_name="main.gold", owner="data-eng")
    tag_service = _FakeUcTagAssignments(
        {("schemas", "main.gold"): [SimpleNamespace(tag_key="tier", tag_value="curated")]}
    )
    ws = _ws(
        catalogs=_FakeService([catalog]),
        schemas=_FakeService([schema]),
        entity_tag_assignments=tag_service,
    )
    (snapshot,) = scan_schemas(ws)
    assert snapshot.attributes["tags"] == {"tier": "curated"}
    assert tag_service.calls == [("schemas", "main.gold")]


def test_scan_external_locations_reads_governed_uc_tags():
    location = SimpleNamespace(name="raw-landing", owner="data-eng", url="s3://bucket/raw")
    tag_service = _FakeUcTagAssignments(
        {("externallocations", "raw-landing"): [SimpleNamespace(tag_key="zone", tag_value="raw")]}
    )
    ws = _ws(external_locations=_FakeService([location]), entity_tag_assignments=tag_service)
    (snapshot,) = scan_external_locations(ws)
    assert snapshot.attributes["tags"] == {"zone": "raw"}
    assert tag_service.calls == [("externallocations", "raw-landing")]


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


class _FakePipelines:
    def __init__(self, pipelines, specs):
        self._pipelines = pipelines
        self._specs = specs

    def list_pipelines(self):
        return list(self._pipelines)

    def get(self, pipeline_id):
        # The scanner fetches the full spec per pipeline; return the matching one.
        return SimpleNamespace(spec=self._specs.get(pipeline_id))


def test_scan_pipelines_reads_spec_fields():
    info = SimpleNamespace(
        pipeline_id="p-1", name="prod_etl", creator_user_name="alice@example.com"
    )
    spec = SimpleNamespace(
        name="prod_etl",
        tags={"team": "data"},
        catalog="main",
        target=None,
        schema="analytics",
        channel="CURRENT",
        edition="ADVANCED",
        continuous=False,
        photon=True,
        serverless=True,
        development=False,
    )
    (snapshot,) = scan_pipelines(_ws(pipelines=_FakePipelines([info], {"p-1": spec})))
    assert snapshot.resource_type is ResourceType.PIPELINE
    attrs = snapshot.attributes
    assert attrs["name"] == "prod_etl"
    assert attrs["owner_type"] == "user"
    assert attrs["tags"] == {"team": "data"}
    assert attrs["catalog"] == "main"
    assert attrs["schema"] == "analytics"
    assert attrs["edition"] == "ADVANCED"
    assert attrs["serverless"] is True
    assert attrs["continuous"] is False


class _FakeGenie:
    def __init__(self, spaces):
        self._spaces = spaces

    def list_spaces(self, page_token=None):
        # Single page; the scanner stops when next_page_token is falsy.
        return SimpleNamespace(spaces=list(self._spaces), next_page_token=None)


def test_scan_genie_spaces_maps_title_and_description():
    documented = SimpleNamespace(
        space_id="sp-1", title="Sales Genie", description="Ask about sales", warehouse_id="wh-9"
    )
    bare = SimpleNamespace(space_id="sp-2", title="Bare", description=None, warehouse_id=None)
    by_id = {s.resource_id: s for s in scan_genie_spaces(_ws(genie=_FakeGenie([documented, bare])))}
    assert set(by_id) == {"sp-1", "sp-2"}
    assert by_id["sp-1"].resource_type is ResourceType.GENIE_SPACE
    attrs = by_id["sp-1"].attributes
    assert attrs["name"] == "Sales Genie"
    assert attrs["warehouse_id"] == "wh-9"
    assert attrs["description"] == "Ask about sales"
    assert attrs["has_description"] is True
    assert by_id["sp-2"].attributes["has_description"] is False


class _PagingGenie:
    """A fake Genie service that serves spaces across multiple pages and records the tokens
    it was called with, so the scanner's pagination loop is exercised end to end."""

    def __init__(self, pages):
        self._pages = pages
        self.seen_tokens = []

    def list_spaces(self, page_token=None):
        self.seen_tokens.append(page_token)
        spaces, next_token = self._pages[page_token]
        return SimpleNamespace(spaces=spaces, next_page_token=next_token)


def test_scan_genie_spaces_follows_pagination():
    page1 = SimpleNamespace(space_id="sp-1", title="One", description="d", warehouse_id="wh-1")
    page2 = SimpleNamespace(space_id="sp-2", title="Two", description=None, warehouse_id="wh-2")
    genie = _PagingGenie(
        {
            None: ([page1], "token-2"),
            "token-2": ([page2], None),
        }
    )
    snapshots = scan_genie_spaces(_ws(genie=genie))
    assert {s.resource_id for s in snapshots} == {"sp-1", "sp-2"}
    # Both pages were fetched, following the token from the first response into the second call.
    assert genie.seen_tokens == [None, "token-2"]


def test_scan_genie_spaces_without_genie_service_raises():
    # A workspace client from an older SDK has no ``genie`` attribute; the scanner should fail
    # with a clear, actionable error rather than an opaque AttributeError.
    with pytest.raises(UnsupportedResourceError):
        scan_genie_spaces(_ws())


class _FakeDatabase:
    def __init__(self, instances):
        self._instances = instances

    def list_database_instances(self):
        # The SDK returns an auto-paginated iterator of DatabaseInstance objects.
        return list(self._instances)


def test_scan_database_instances_maps_state_owner_and_tags():
    instance = SimpleNamespace(
        name="prod_orders",
        creator="alice@example.com",
        creation_time="2026-01-02T03:04:05Z",
        custom_tags=[
            SimpleNamespace(key="team", value="data"),
            SimpleNamespace(key="pii", value=None),
        ],
        capacity="CU_2",
        state=SimpleNamespace(value="AVAILABLE"),
        node_count=2,
        pg_version="16",
        stopped=False,
        enable_readable_secondaries=True,
        retention_window_in_days=7,
    )
    (snapshot,) = scan_database_instances(_ws(database=_FakeDatabase([instance])))
    attrs = snapshot.attributes
    assert snapshot.resource_type is ResourceType.DATABASE_INSTANCE
    assert attrs["id"] == "prod_orders"
    assert attrs["owner_type"] == "user"
    # custom_tags is a list of {key, value}; a null value normalizes to "".
    assert attrs["tags"] == {"team": "data", "pii": ""}
    assert attrs["capacity"] == "CU_2"
    assert attrs["state"] == "AVAILABLE"
    assert attrs["node_count"] == 2
    assert attrs["enable_readable_secondaries"] is True
    assert attrs["retention_window_in_days"] == 7


def test_scan_database_instances_reports_untagged_and_unknown_owner():
    instance = SimpleNamespace(name="scratch", creator=None, custom_tags=None)
    (snapshot,) = scan_database_instances(_ws(database=_FakeDatabase([instance])))
    attrs = snapshot.attributes
    assert attrs["tags"] == {}
    assert attrs["owner_type"] == "unknown"
    assert attrs["state"] is None


def test_scan_database_instances_without_database_service_raises():
    # An older SDK without the database API should fail with a clear, actionable error.
    with pytest.raises(UnsupportedResourceError):
        scan_database_instances(_ws())


class _FakeAlertsV2:
    def __init__(self, alerts):
        self._alerts = alerts

    def list_alerts(self):
        # The v2 SDK returns an auto-paginated iterator of AlertV2 objects.
        return list(self._alerts)


def test_scan_sql_alerts_reads_evaluation_and_owner():
    alert = SimpleNamespace(
        id="a-1",
        display_name="prod_row_count",
        owner_user_name="alice@example.com",
        create_time="2026-01-02T03:04:05Z",
        warehouse_id="wh-9",
        run_as_user_name="alice@example.com",
        lifecycle_state=SimpleNamespace(value="ACTIVE"),
        schedule=SimpleNamespace(quartz_cron_schedule="0 0 * * * ?"),
        evaluation=SimpleNamespace(
            state=SimpleNamespace(value="OK"),
            comparison_operator=SimpleNamespace(value="GREATER_THAN"),
            empty_result_state=SimpleNamespace(value="UNKNOWN"),
        ),
    )
    (snapshot,) = scan_sql_alerts(_ws(alerts_v2=_FakeAlertsV2([alert])))
    attrs = snapshot.attributes
    assert snapshot.resource_type is ResourceType.SQL_ALERT
    assert attrs["name"] == "prod_row_count"
    assert attrs["owner_type"] == "user"
    assert attrs["created_time"] is not None
    assert attrs["warehouse_id"] == "wh-9"
    assert attrs["state"] == "OK"
    assert attrs["lifecycle_state"] == "ACTIVE"
    assert attrs["comparison_operator"] == "GREATER_THAN"
    assert attrs["empty_result_state"] == "UNKNOWN"
    assert attrs["has_schedule"] is True
    assert "tags" not in attrs  # alerts do not advertise tags


def test_scan_sql_alerts_handles_missing_evaluation_and_schedule():
    alert = SimpleNamespace(
        id="a-2", display_name="adhoc", owner_user_name=None, evaluation=None, schedule=None
    )
    (snapshot,) = scan_sql_alerts(_ws(alerts_v2=_FakeAlertsV2([alert])))
    attrs = snapshot.attributes
    assert attrs["owner_type"] == "unknown"
    assert attrs["state"] is None
    assert attrs["comparison_operator"] is None
    assert attrs["has_schedule"] is False


def test_scan_sql_alerts_without_alerts_v2_service_raises():
    # An older SDK without the v2 alerts API should fail with a clear, actionable error.
    with pytest.raises(UnsupportedResourceError):
        scan_sql_alerts(_ws())


class _FakeDataQuality:
    def __init__(self, monitors):
        self._monitors = monitors

    def list_monitor(self):
        # The data-quality SDK returns an auto-paginated iterator of Monitor objects.
        return list(self._monitors)


def _monitor(profiling):
    return SimpleNamespace(object_type="table", object_id="obj-1", data_profiling_config=profiling)


class _RaisingCatalogs:
    def __init__(self, error):
        self._error = error

    def list(self):
        raise self._error


def test_scan_quality_monitors_reads_data_profiling_config():
    profiling = SimpleNamespace(
        monitored_table_name="main.gold.orders",
        output_schema_id="sch-123",
        snapshot=SimpleNamespace(),
        time_series=None,
        inference_log=None,
        schedule=SimpleNamespace(quartz_cron_expression="0 0 * * * ?"),
    )
    catalog = SimpleNamespace(name="main")
    schema = SimpleNamespace(schema_id="sch-123", full_name="main.monitoring", name="monitoring")
    ws = _ws(
        data_quality=_FakeDataQuality([_monitor(profiling)]),
        catalogs=_FakeService([catalog]),
        schemas=_FakeService([schema]),
    )
    (snapshot,) = scan_quality_monitors(ws)
    attrs = snapshot.attributes
    assert snapshot.resource_type is ResourceType.QUALITY_MONITOR
    assert attrs["id"] == "main.gold.orders"
    assert attrs["table_name"] == "main.gold.orders"
    assert attrs["output_schema_id"] == "sch-123"
    assert attrs["output_schema_name"] == "main.monitoring"
    assert attrs["monitor_type"] == "snapshot"
    assert attrs["has_schedule"] is True
    # Quality monitors are neither owned nor tagged.
    assert "owner" not in attrs and "tags" not in attrs


def test_scan_quality_monitors_leaves_output_schema_name_none_when_unresolved():
    profiling = SimpleNamespace(
        monitored_table_name="main.gold.orders",
        output_schema_id="sch-missing",
        snapshot=SimpleNamespace(),
        time_series=None,
        inference_log=None,
        schedule=None,
    )
    ws = _ws(
        data_quality=_FakeDataQuality([_monitor(profiling)]),
        catalogs=_FakeService([SimpleNamespace(name="main")]),
        schemas=_FakeService([SimpleNamespace(schema_id="sch-other", full_name="main.other")]),
    )
    (snapshot,) = scan_quality_monitors(ws)
    assert snapshot.attributes["output_schema_id"] == "sch-missing"
    assert snapshot.attributes["output_schema_name"] is None


def test_scan_quality_monitors_resolution_tolerates_listing_errors():
    from databricks.sdk.errors import PermissionDenied

    profiling = SimpleNamespace(
        monitored_table_name="main.gold.orders",
        output_schema_id="sch-123",
        snapshot=SimpleNamespace(),
        time_series=None,
        inference_log=None,
        schedule=None,
    )
    ws = _ws(
        data_quality=_FakeDataQuality([_monitor(profiling)]),
        catalogs=_RaisingCatalogs(PermissionDenied("no access")),
        schemas=_FakeService([]),
    )
    (snapshot,) = scan_quality_monitors(ws)
    assert snapshot.attributes["output_schema_id"] == "sch-123"
    assert snapshot.attributes["output_schema_name"] is None


def test_scan_quality_monitors_falls_back_to_object_id_when_table_name_missing():
    # A data-profiling monitor with no monitored_table_name falls back to object_id
    profiling = SimpleNamespace(
        monitored_table_name=None,
        output_schema_id="main.monitoring",
        snapshot=SimpleNamespace(),
        time_series=None,
        inference_log=None,
        schedule=None,
    )
    ws = _ws(data_quality=_FakeDataQuality([_monitor(profiling)]))
    (snapshot,) = scan_quality_monitors(ws)
    attrs = snapshot.attributes
    assert attrs["table_name"] is None
    # _monitor(...) uses object_id "obj-1"; id and name both fall back to it.
    assert attrs["id"] == "obj-1"
    assert attrs["name"] == "obj-1"


def test_scan_quality_monitors_skips_monitors_without_profiling_config():
    profiling = SimpleNamespace(
        monitored_table_name="main.gold.inference",
        output_schema_id="main.monitoring",
        snapshot=None,
        time_series=None,
        inference_log=SimpleNamespace(),
        schedule=None,
    )
    # An anomaly-detection-only monitor has no data_profiling_config and is skipped.
    ws = _ws(data_quality=_FakeDataQuality([_monitor(profiling), _monitor(None)]))
    snapshots = scan_quality_monitors(ws)
    assert [s.attributes["monitor_type"] for s in snapshots] == ["inference_log"]
    assert snapshots[0].attributes["has_schedule"] is False


def test_scan_quality_monitors_without_data_quality_service_raises():
    # An older SDK without the data-quality API should fail with a clear, actionable error.
    with pytest.raises(UnsupportedResourceError):
        scan_quality_monitors(_ws())


class _RaisingDataQuality:
    def __init__(self, error):
        self._error = error

    def list_monitor(self):
        raise self._error


def test_scan_quality_monitors_wraps_api_errors_in_scan_error():
    from databricks.sdk.errors import PermissionDenied

    ws = _ws(data_quality=_RaisingDataQuality(PermissionDenied("feature not enabled")))
    with pytest.raises(ScanError):
        scan_quality_monitors(ws)


def test_scan_genie_spaces_reads_governed_tags():
    space = SimpleNamespace(
        space_id="sp-1", title="Sales", description="Sales Q&A", warehouse_id="wh-1"
    )
    tag_service = _FakeTagAssignments(
        {("geniespaces", "sp-1"): [SimpleNamespace(tag_key="team", tag_value="sales")]}
    )
    ws = _ws(genie=_FakeGenie([space]), workspace_entity_tag_assignments=tag_service)
    (snapshot,) = scan_genie_spaces(ws)
    # Tags come from the entity-tag-assignments API, keyed by the geniespaces entity type + id.
    assert snapshot.attributes["tags"] == {"team": "sales"}
    assert tag_service.calls == [("geniespaces", "sp-1")]


def test_scan_genie_spaces_without_tag_service_reports_untagged():
    space = SimpleNamespace(space_id="sp-1", title="Sales", description=None, warehouse_id=None)
    (snapshot,) = scan_genie_spaces(_ws(genie=_FakeGenie([space])))
    assert snapshot.attributes["tags"] == {}
