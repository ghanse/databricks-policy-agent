import json

import pytest

from policy_agent.enforce import load_bundle_config, run_gate, snapshot_bundle
from policy_agent.enforce.bundle import resolve_bundle
from policy_agent.enforce.model import GateVerdict
from policy_agent.errors import EnforcementError
from policy_agent.policy import allow, leaf
from policy_agent.policy.model import EnforcementLevel, ResourceType

BUNDLE = {
    "resources": {
        "jobs": {
            "etl": {
                "name": "prod_etl",
                "tags": {"team": "data"},
                "email_notifications": {"on_failure": ["oncall@example.com"]},
                "run_as": {"service_principal_name": "11111111-1111-1111-1111-111111111111"},
            },
            "adhoc": {"name": "adhoc"},
        }
    }
}


def _snapshots():
    return snapshot_bundle(BUNDLE)


def test_snapshot_bundle_maps_declared_jobs():
    by_id = {snapshot.resource_id: snapshot for snapshot in _snapshots()}
    assert set(by_id) == {"etl", "adhoc"}
    etl = by_id["etl"].attributes
    assert by_id["etl"].resource_type is ResourceType.JOB
    assert etl["tags"] == {"team": "data"}
    assert etl["has_email_notifications"] is True
    assert etl["owner_type"] == "service_principal"
    adhoc = by_id["adhoc"].attributes
    assert adhoc["tags"] == {}
    assert adhoc["has_email_notifications"] is False
    assert adhoc["owner_type"] == "unknown"


def test_snapshot_bundle_maps_declared_sql_warehouses():
    # A warehouse policy must see declared warehouses; otherwise a non-compliant bundle would
    # pass because the gate evaluated zero resources.
    config = {
        "resources": {
            "sql_warehouses": {
                "reporting": {
                    "name": "reporting_wh",
                    "cluster_size": "2X-Large",
                    "auto_stop_mins": 10,
                    "enable_serverless_compute": True,
                    "tags": {"custom_tags": [{"key": "team", "value": "data"}]},
                }
            }
        }
    }
    (snapshot,) = snapshot_bundle(config)
    assert snapshot.resource_type is ResourceType.SQL_WAREHOUSE
    attrs = snapshot.attributes
    assert attrs["cluster_size"] == "2X-Large"
    assert attrs["auto_stop_minutes"] == 10
    assert attrs["enable_serverless_compute"] is True
    # Warehouse tags use the {custom_tags: [{key, value}]} shape, unlike the flat job dict.
    assert attrs["tags"] == {"team": "data"}

    oversized = allow("wh-size", "sql_warehouse", leaf("cluster_size", "equals", "Medium"))
    result = run_gate([oversized], snapshot_bundle(config), fail_on=EnforcementLevel.ADVISORY)
    assert result.blocked


def test_snapshot_bundle_maps_declared_clusters():
    # Clusters use cluster_name and a flat custom_tags mapping, unlike jobs.
    config = {
        "resources": {
            "clusters": {
                "analytics": {
                    "cluster_name": "analytics",
                    "custom_tags": {"team": "data"},
                    "autotermination_minutes": 0,
                    "node_type_id": "i3.xlarge",
                    "spark_version": "14.3.x-scala2.12",
                }
            }
        }
    }
    (snapshot,) = snapshot_bundle(config)
    assert snapshot.resource_type is ResourceType.CLUSTER
    attrs = snapshot.attributes
    assert attrs["name"] == "analytics"
    assert attrs["tags"] == {"team": "data"}
    assert attrs["autotermination_minutes"] == 0
    assert attrs["node_type_id"] == "i3.xlarge"

    # autotermination disabled (0) fails a "must auto-terminate within 120 min" policy.
    must_autoterminate = allow(
        "cluster-autoterm", "cluster", leaf("autotermination_minutes", "ttl_within", 120)
    )
    result = run_gate(
        [must_autoterminate], snapshot_bundle(config), fail_on=EnforcementLevel.ADVISORY
    )
    assert result.blocked
    assert {f.resource_id for f in result.blocking} == {"analytics"}


def test_snapshot_bundle_maps_declared_apps():
    config = {"resources": {"apps": {"dashboard": {"name": "team_dashboard"}}}}
    (snapshot,) = snapshot_bundle(config)
    assert snapshot.resource_type is ResourceType.APP
    attrs = snapshot.attributes
    assert attrs["name"] == "team_dashboard"
    assert attrs["tags"] == {}
    # App status/compute are runtime-only and not declarable, so they stay unknown.
    assert attrs["app_status"] is None

    prod_only = allow("app-naming", "app", leaf("name", "matches_regex", "^prod_.+$"))
    result = run_gate([prod_only], snapshot_bundle(config), fail_on=EnforcementLevel.ADVISORY)
    assert result.blocked
    assert {f.resource_id for f in result.blocking} == {"dashboard"}


def test_snapshot_bundle_maps_declared_serving_endpoints():
    # Declared under the model_serving_endpoints group; distinct scalar fields.
    config = {
        "resources": {
            "model_serving_endpoints": {
                "llm": {
                    "name": "llm_gateway",
                    "endpoint_type": "FOUNDATION_MODEL_API",
                    "budget_policy_id": "bp-1",
                    "route_optimized": False,
                }
            }
        }
    }
    (snapshot,) = snapshot_bundle(config)
    assert snapshot.resource_type is ResourceType.SERVING_ENDPOINT
    attrs = snapshot.attributes
    assert attrs["name"] == "llm_gateway"
    assert attrs["endpoint_type"] == "FOUNDATION_MODEL_API"
    assert attrs["budget_policy_id"] == "bp-1"
    assert attrs["route_optimized"] is False

    require_route_optimized = allow(
        "endpoint-route-optimized", "serving_endpoint", leaf("route_optimized", "equals", True)
    )
    result = run_gate(
        [require_route_optimized], snapshot_bundle(config), fail_on=EnforcementLevel.ADVISORY
    )
    assert result.blocked
    assert {f.resource_id for f in result.blocking} == {"llm"}


def test_snapshot_bundle_maps_declared_uc_objects():
    config = {
        "resources": {
            "catalogs": {"main": {"name": "main", "isolation_mode": "ISOLATED"}},
            "schemas": {"gold": {"name": "gold", "catalog_name": "main"}},
            "volumes": {
                "landing": {
                    "name": "landing",
                    "catalog_name": "main",
                    "schema_name": "gold",
                    "volume_type": "MANAGED",
                }
            },
            "registered_models": {
                "churn": {"name": "churn", "catalog_name": "main", "schema_name": "ml"}
            },
            "external_locations": {
                "raw": {"name": "raw", "url": "s3://bucket/raw", "read_only": False}
            },
            "secret_scopes": {"prod": {"name": "prod", "backend_type": "DATABRICKS"}},
        }
    }
    by_type = {s.resource_type: s.attributes for s in snapshot_bundle(config)}
    assert by_type[ResourceType.CATALOG]["isolation_mode"] == "ISOLATED"
    assert by_type[ResourceType.SCHEMA]["catalog_name"] == "main"
    assert by_type[ResourceType.VOLUME]["volume_type"] == "MANAGED"
    assert by_type[ResourceType.REGISTERED_MODEL]["schema_name"] == "ml"
    assert by_type[ResourceType.EXTERNAL_LOCATION]["url"] == "s3://bucket/raw"
    assert by_type[ResourceType.SECRET_SCOPE]["backend_type"] == "DATABRICKS"
    # Catalogs, schemas, volumes, and external locations are taggable (tags governed via the UC
    # entity-tag-assignments API); a bundle rarely declares them, so they default to empty.
    for taggable in (
        ResourceType.CATALOG,
        ResourceType.SCHEMA,
        ResourceType.VOLUME,
        ResourceType.EXTERNAL_LOCATION,
    ):
        assert by_type[taggable]["tags"] == {}
    # Registered models and secret scopes are not taggable.
    assert "tags" not in by_type[ResourceType.REGISTERED_MODEL]
    assert "tags" not in by_type[ResourceType.SECRET_SCOPE]

    # An external location that is not read-only violates a read-only policy at the gate.
    read_only = allow("el-read-only", "external_location", leaf("read_only", "equals", True))
    result = run_gate([read_only], snapshot_bundle(config), fail_on=EnforcementLevel.ADVISORY)
    assert {f.resource_id for f in result.blocking} == {"raw"}


def test_snapshot_bundle_maps_quality_monitors_enforce_only():
    config = {
        "resources": {
            "quality_monitors": {
                "orders": {
                    "table_name": "main.gold.orders",
                    "output_schema_name": "main.monitoring",
                    "schedule": {"quartz_cron_expression": "0 0 * * * ?"},
                    "snapshot": {},
                },
                "adhoc": {"table_name": "main.gold.adhoc", "inference_log": {}},
            }
        }
    }
    by_id = {s.resource_id: s for s in snapshot_bundle(config)}
    assert by_id["orders"].resource_type is ResourceType.QUALITY_MONITOR
    assert by_id["orders"].attributes["table_name"] == "main.gold.orders"
    # Bundles declare the output schema by name; the id is a live-scan-only attribute.
    assert by_id["orders"].attributes["output_schema_name"] == "main.monitoring"
    assert by_id["orders"].attributes["output_schema_id"] is None
    assert by_id["orders"].attributes["monitor_type"] == "snapshot"
    assert by_id["orders"].attributes["has_schedule"] is True
    assert by_id["adhoc"].attributes["monitor_type"] == "inference_log"
    assert by_id["adhoc"].attributes["has_schedule"] is False

    # Monitors must be scheduled; the ad-hoc one violates.
    scheduled = allow("qm-scheduled", "quality_monitor", leaf("has_schedule", "equals", True))
    result = run_gate([scheduled], snapshot_bundle(config), fail_on=EnforcementLevel.ADVISORY)
    assert {f.resource_id for f in result.blocking} == {"adhoc"}


def test_snapshot_bundle_maps_declared_pipelines():
    config = {
        "resources": {
            "pipelines": {
                "ingest": {
                    "name": "prod_ingest",
                    "catalog": "main",
                    "schema": "bronze",
                    "edition": "ADVANCED",
                    "serverless": True,
                    "continuous": False,
                    "tags": {"team": "data"},
                }
            }
        }
    }
    (snapshot,) = snapshot_bundle(config)
    assert snapshot.resource_type is ResourceType.PIPELINE
    attrs = snapshot.attributes
    assert attrs["name"] == "prod_ingest"
    assert attrs["catalog"] == "main"
    assert attrs["schema"] == "bronze"
    assert attrs["serverless"] is True
    assert attrs["tags"] == {"team": "data"}

    # A non-serverless pipeline violates a "must be serverless" policy.
    must_be_serverless = allow(
        "pipeline-serverless", "pipeline", leaf("serverless", "equals", True)
    )
    classic = {"resources": {"pipelines": {"legacy": {"name": "legacy", "serverless": False}}}}
    result = run_gate(
        [must_be_serverless], snapshot_bundle(classic), fail_on=EnforcementLevel.ADVISORY
    )
    assert result.blocked
    assert {f.resource_id for f in result.blocking} == {"legacy"}


def test_snapshot_bundle_maps_declared_genie_spaces():
    config = {
        "resources": {
            "genie_spaces": {
                "sales": {"title": "Sales", "warehouse_id": "wh-1", "description": "Sales Q&A"},
                "adhoc": {"title": "Adhoc", "warehouse_id": "wh-2"},
            }
        }
    }
    by_id = {s.resource_id: s for s in snapshot_bundle(config)}
    assert set(by_id) == {"sales", "adhoc"}
    assert by_id["sales"].resource_type is ResourceType.GENIE_SPACE
    assert by_id["sales"].attributes["name"] == "Sales"
    assert by_id["sales"].attributes["warehouse_id"] == "wh-1"
    assert by_id["sales"].attributes["has_description"] is True
    assert by_id["adhoc"].attributes["has_description"] is False
    # Genie spaces advertise tags (governed via tag assignments); a bundle rarely declares them,
    # so they default to empty.
    assert by_id["sales"].attributes["tags"] == {}

    # A Genie space without a description violates a "must be documented" policy.
    documented = allow("genie-documented", "genie_space", leaf("has_description", "equals", True))
    result = run_gate([documented], snapshot_bundle(config), fail_on=EnforcementLevel.ADVISORY)
    assert result.blocked
    assert {f.resource_id for f in result.blocking} == {"adhoc"}


def test_snapshot_bundle_maps_declared_alerts():
    # Alerts are declared under the `alerts` group using the v2 schema.
    config = {
        "resources": {
            "alerts": {
                "row_count": {
                    "display_name": "prod_row_count",
                    "warehouse_id": "wh-1",
                    "schedule": {"quartz_cron_schedule": "0 0 * * * ?"},
                    "evaluation": {
                        "comparison_operator": "GREATER_THAN",
                        "empty_result_state": "UNKNOWN",
                    },
                }
            }
        }
    }
    (snapshot,) = snapshot_bundle(config)
    assert snapshot.resource_type is ResourceType.SQL_ALERT
    attrs = snapshot.attributes
    assert attrs["name"] == "prod_row_count"
    assert attrs["warehouse_id"] == "wh-1"
    assert attrs["comparison_operator"] == "GREATER_THAN"
    assert attrs["has_schedule"] is True
    # State is runtime-only and unknown from a bundle; alerts carry no tags.
    assert attrs["state"] is None
    assert "tags" not in attrs

    # An alert without a warehouse violates a "must run on a warehouse" policy at the gate.
    needs_warehouse = allow("alert-warehouse", "sql_alert", leaf("warehouse_id", "exists"))
    unattached = {"resources": {"alerts": {"orphan": {"display_name": "orphan"}}}}
    result = run_gate(
        [needs_warehouse], snapshot_bundle(unattached), fail_on=EnforcementLevel.ADVISORY
    )
    assert result.blocked
    assert {f.resource_id for f in result.blocking} == {"orphan"}


def test_snapshot_bundle_derives_job_task_attributes():
    # has_retry_policy / uses_serverless_compute come from the declared tasks, matching the
    # live scanner; otherwise they default to None and every job falsely violates such policies.
    config = {
        "resources": {
            "jobs": {
                "serverless_retried": {
                    "name": "prod_etl",
                    "tasks": [{"task_key": "main", "max_retries": 3}],
                },
                "classic_no_retry": {
                    "name": "adhoc",
                    "tasks": [{"task_key": "main", "existing_cluster_id": "c-1"}],
                },
            }
        }
    }
    by_id = {s.resource_id: s.attributes for s in snapshot_bundle(config)}
    assert by_id["serverless_retried"]["has_retry_policy"] is True
    assert by_id["serverless_retried"]["uses_serverless_compute"] is True
    assert by_id["classic_no_retry"]["has_retry_policy"] is False
    assert by_id["classic_no_retry"]["uses_serverless_compute"] is False


def test_run_gate_requires_reason_for_overrides():
    tagged = allow(
        "jobs-tagged", ResourceType.JOB, leaf("tags", "has_tag", "team"), enforcement_level="soft"
    )
    with pytest.raises(EnforcementError, match="override reason is required"):
        run_gate(
            [tagged],
            _snapshots(),
            fail_on=EnforcementLevel.SOFT,
            overrides=frozenset({"jobs-tagged"}),
            override_reason="   ",
        )


def test_soft_violation_warns_below_threshold_but_blocks_at_threshold():
    tagged = allow(
        "jobs-tagged", ResourceType.JOB, leaf("tags", "has_tag", "team"), enforcement_level="soft"
    )

    lenient = run_gate([tagged], _snapshots(), fail_on=EnforcementLevel.HARD)
    assert lenient.verdict is GateVerdict.PASS_WITH_WARNINGS
    assert not lenient.blocked
    assert {f.resource_id for f in lenient.warnings} == {"adhoc"}

    strict = run_gate([tagged], _snapshots(), fail_on=EnforcementLevel.SOFT)
    assert strict.blocked
    assert {f.resource_id for f in strict.blocking} == {"adhoc"}


def test_soft_violation_can_be_overridden():
    tagged = allow(
        "jobs-tagged", ResourceType.JOB, leaf("tags", "has_tag", "team"), enforcement_level="soft"
    )
    result = run_gate(
        [tagged],
        _snapshots(),
        fail_on=EnforcementLevel.SOFT,
        overrides=frozenset({"jobs-tagged"}),
        override_reason="tracked in JIRA-123",
    )
    assert not result.blocked
    assert result.verdict is GateVerdict.PASS_WITH_WARNINGS
    assert {f.resource_id for f in result.overridden} == {"adhoc"}


def test_hard_violation_blocks_and_cannot_be_overridden():
    must_notify = allow(
        "jobs-notify",
        ResourceType.JOB,
        leaf("has_email_notifications", "equals", True),
        enforcement_level="hard",
    )
    result = run_gate(
        [must_notify],
        _snapshots(),
        fail_on=EnforcementLevel.HARD,
        overrides=frozenset({"jobs-notify"}),
        override_reason="attempted override",
    )
    assert result.blocked
    assert {f.resource_id for f in result.blocking} == {"adhoc"}
    assert result.overridden == ()


def test_clean_bundle_passes_with_fixes_suggested():
    tagged = allow(
        "jobs-tagged", ResourceType.JOB, leaf("tags", "has_tag", "team"), enforcement_level="hard"
    )
    result = run_gate(
        [tagged], _snapshots(), fail_on=EnforcementLevel.HARD, suggest_remediations=True
    )
    assert result.blocked
    assert [fix.resource_id for fix in result.fixes] == ["adhoc"]
    assert result.to_dict()["verdict"] == "blocked"


def test_load_bundle_config_from_json_file(tmp_path):
    path = tmp_path / "resolved.json"
    path.write_text(json.dumps(BUNDLE), encoding="utf-8")
    assert load_bundle_config(path)["resources"]["jobs"]["etl"]["name"] == "prod_etl"


def test_resolve_bundle_reports_missing_directory(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(EnforcementError, match="Bundle directory does not exist"):
        resolve_bundle(missing)


def test_resolve_bundle_reports_missing_file(tmp_path):
    missing = tmp_path / "not_exists.json"
    with pytest.raises(EnforcementError, match=f"Bundle JSON file does not exist: {missing}"):
        load_bundle_config(missing)
