"""Maps a resolved bundle configuration into evaluable resource snapshots.

Each declared resource under ``resources.<group>.<key>`` is normalised into the same
`ResourceSnapshot` shape produced by a live scan, so the enforcement gate reuses the
existing evaluation engine unchanged. Only *declarable* attributes are populated; attributes
known only at runtime (for example ``created_time``) are ``None``.
"""

from __future__ import annotations

from typing import Any

from policy_agent.policy.model import (
    OWNER_TYPE_SERVICE_PRINCIPAL,
    OWNER_TYPE_UNKNOWN,
    OWNER_TYPE_USER,
    ResourceType,
)
from policy_agent.scan.results import ResourceSnapshot

_RESOURCE_GROUPS: dict[str, ResourceType] = {
    "jobs": ResourceType.JOB,
    "clusters": ResourceType.CLUSTER,
    "sql_warehouses": ResourceType.SQL_WAREHOUSE,
    "apps": ResourceType.APP,
    "model_serving_endpoints": ResourceType.SERVING_ENDPOINT,
    "catalogs": ResourceType.CATALOG,
    "schemas": ResourceType.SCHEMA,
    "volumes": ResourceType.VOLUME,
    "registered_models": ResourceType.REGISTERED_MODEL,
    "external_locations": ResourceType.EXTERNAL_LOCATION,
    "secret_scopes": ResourceType.SECRET_SCOPE,
    "quality_monitors": ResourceType.QUALITY_MONITOR,
    "pipelines": ResourceType.PIPELINE,
    "genie_spaces": ResourceType.GENIE_SPACE,
    "alerts": ResourceType.SQL_ALERT,
}


def snapshot_bundle(config: dict[str, Any]) -> list[ResourceSnapshot]:
    """Builds resource snapshots from a resolved bundle configuration.

    Args:
        config: A resolved bundle configuration (see `load_bundle_config`).

    Returns:
        One snapshot per supported declared resource, in resource-group order.
    """
    resources = config.get("resources") or {}
    snapshots: list[ResourceSnapshot] = []
    for group, resource_type in _RESOURCE_GROUPS.items():
        for key, definition in (resources.get(group) or {}).items():
            attributes = _COMMON[resource_type](key, definition)
            snapshots.append(ResourceSnapshot(resource_type=resource_type, attributes=attributes))
    return snapshots


def _job_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    owner, owner_type = _run_as_owner(definition.get("run_as"))
    schedule = definition.get("schedule") or {}
    notifications = definition.get("email_notifications") or {}
    tasks = definition.get("tasks") or []
    return {
        **_common(key, definition.get("name"), owner, owner_type, definition.get("tags")),
        "schedule_pause_status": schedule.get("pause_status"),
        "max_concurrent_runs": definition.get("max_concurrent_runs"),
        "timeout_seconds": definition.get("timeout_seconds"),
        "run_as_type": owner_type,
        "has_email_notifications": bool(notifications.get("on_failure")),
        "has_retry_policy": _all_tasks(tasks, _task_has_retries),
        "uses_serverless_compute": _all_tasks(tasks, _task_is_serverless),
        "format": definition.get("format"),
    }


def _all_tasks(tasks: Any, predicate: Any) -> bool:
    # Mirror the live scanner: a job satisfies a per-task property only when it has tasks and
    # every task satisfies it.
    return bool(tasks) and all(predicate(task) for task in tasks)


def _task_has_retries(task: dict[str, Any]) -> bool:
    max_retries = task.get("max_retries")
    # A task retries when max_retries is a nonzero count; -1 means unlimited, 0 means never.
    return (
        isinstance(max_retries, int)
        and not isinstance(max_retries, bool)
        and (max_retries == -1 or max_retries > 0)
    )


def _task_is_serverless(task: dict[str, Any]) -> bool:
    # A serverless task references no classic compute: no interactive cluster, no task-defined
    # job cluster, and no shared job-cluster key.
    return (
        task.get("existing_cluster_id") is None
        and task.get("new_cluster") is None
        and task.get("job_cluster_key") is None
    )


def _cluster_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_common(
            key,
            definition.get("cluster_name"),
            None,
            OWNER_TYPE_UNKNOWN,
            definition.get("custom_tags"),
        ),
        "cluster_source": definition.get("cluster_source"),
        "autotermination_minutes": definition.get("autotermination_minutes"),
        "spark_version": definition.get("spark_version"),
        "node_type_id": definition.get("node_type_id"),
        "num_workers": definition.get("num_workers"),
        "data_security_mode": definition.get("data_security_mode"),
        "single_user_name": definition.get("single_user_name"),
    }


def _sql_warehouse_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_common(key, definition.get("name"), None, OWNER_TYPE_UNKNOWN, definition.get("tags")),
        "warehouse_type": definition.get("warehouse_type"),
        "cluster_size": definition.get("cluster_size"),
        "auto_stop_minutes": definition.get("auto_stop_mins"),
        "enable_serverless_compute": definition.get("enable_serverless_compute"),
        "min_num_clusters": definition.get("min_num_clusters"),
        "max_num_clusters": definition.get("max_num_clusters"),
    }


def _app_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_common(key, definition.get("name"), None, OWNER_TYPE_UNKNOWN, definition.get("tags")),
        "app_status": None,
        "compute_status": None,
        "active_deployment_mode": None,
    }


def _serving_endpoint_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_common(key, definition.get("name"), None, OWNER_TYPE_UNKNOWN, definition.get("tags")),
        "endpoint_state": None,
        "endpoint_type": definition.get("endpoint_type"),
        "budget_policy_id": definition.get("budget_policy_id"),
        "route_optimized": definition.get("route_optimized"),
    }


def _catalog_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_owned(key, definition.get("name")),
        "comment": definition.get("comment"),
        "catalog_type": definition.get("catalog_type"),
        "isolation_mode": definition.get("isolation_mode"),
        "storage_root": definition.get("storage_root"),
    }


def _schema_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_owned(key, definition.get("name")),
        "comment": definition.get("comment"),
        "catalog_name": definition.get("catalog_name"),
    }


def _volume_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_owned(key, definition.get("name")),
        "comment": definition.get("comment"),
        "catalog_name": definition.get("catalog_name"),
        "schema_name": definition.get("schema_name"),
        "volume_type": definition.get("volume_type"),
    }


def _registered_model_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_owned(key, definition.get("name")),
        "comment": definition.get("comment"),
        "catalog_name": definition.get("catalog_name"),
        "schema_name": definition.get("schema_name"),
    }


def _external_location_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_owned(key, definition.get("name")),
        "comment": definition.get("comment"),
        "url": definition.get("url"),
        "credential_name": definition.get("credential_name"),
        "read_only": definition.get("read_only"),
        "isolation_mode": definition.get("isolation_mode"),
    }


def _secret_scope_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": key,
        "name": definition.get("name") or key,
        "backend_type": definition.get("backend_type"),
    }


def _quality_monitor_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": key,
        "name": definition.get("table_name") or key,
        "table_name": definition.get("table_name"),
        "output_schema_name": definition.get("output_schema_name"),
        "monitor_type": _monitor_type(definition),
        "has_schedule": bool(definition.get("schedule")),
    }


def _monitor_type(definition: dict[str, Any]) -> str | None:
    # A quality monitor declares exactly one of these profile blocks.
    for kind in ("snapshot", "time_series", "inference_log"):
        if definition.get(kind) is not None:
            return kind
    return None


def _owned(key: str, name: str | None) -> dict[str, Any]:
    # UC objects have an owner and a creation time (unknown from a bundle) but no tags.
    return {
        "id": key,
        "name": name or key,
        "owner": None,
        "owner_type": OWNER_TYPE_UNKNOWN,
        "created_time": None,
    }


def _pipeline_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_common(key, definition.get("name"), None, OWNER_TYPE_UNKNOWN, definition.get("tags")),
        "catalog": definition.get("catalog"),
        "target": definition.get("target"),
        "schema": definition.get("schema"),
        "channel": definition.get("channel"),
        "edition": definition.get("edition"),
        "continuous": definition.get("continuous"),
        "photon": definition.get("photon"),
        "serverless": definition.get("serverless"),
        "development": definition.get("development"),
    }


def _genie_space_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    # NOTE: Genie spaces have no owner or tags, so this does not use _common
    description = definition.get("description")
    return {
        "id": key,
        "name": definition.get("title") or definition.get("name") or key,
        "warehouse_id": definition.get("warehouse_id"),
        "description": description,
        "has_description": bool(description),
    }


def _sql_alert_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    # Alerts are declared under `resources.alerts` using the v2 schema. Owner and evaluation
    # state are runtime-only and unknown from a bundle; the comparison is declared inline.
    evaluation = definition.get("evaluation") or {}
    run_as = definition.get("run_as")
    run_as_user = run_as.get("user_name") if isinstance(run_as, dict) else None
    return {
        **_owned(key, definition.get("display_name") or definition.get("name")),
        "warehouse_id": definition.get("warehouse_id"),
        "run_as_user_name": run_as_user,
        "state": None,
        "lifecycle_state": None,
        "comparison_operator": evaluation.get("comparison_operator"),
        "empty_result_state": evaluation.get("empty_result_state"),
        "has_schedule": bool(definition.get("schedule")),
    }


def _common(
    key: str,
    name: str | None,
    owner: str | None,
    owner_type: str,
    tags: Any,
) -> dict[str, Any]:
    return {
        "id": key,
        "name": name or key,
        "owner": owner,
        "owner_type": owner_type,
        "tags": _normalize_tags(tags),
        "created_time": None,
    }


def _run_as_owner(run_as: Any) -> tuple[str | None, str]:
    if not isinstance(run_as, dict):
        return None, OWNER_TYPE_UNKNOWN
    service_principal = run_as.get("service_principal_name")
    if service_principal:
        return service_principal, OWNER_TYPE_SERVICE_PRINCIPAL
    user = run_as.get("user_name")
    if user:
        return user, OWNER_TYPE_USER
    return None, OWNER_TYPE_UNKNOWN


def _normalize_tags(tags: Any) -> dict[str, str]:
    if isinstance(tags, dict):
        # SQL warehouses declare tags as {"custom_tags": [{"key": ..., "value": ...}]};
        # jobs and clusters use a flat {key: value} mapping.
        custom_tags = tags.get("custom_tags")
        if isinstance(custom_tags, list):
            return {
                str(pair["key"]): str(pair.get("value", ""))
                for pair in custom_tags
                if isinstance(pair, dict) and "key" in pair
            }
        return {str(key): str(value) for key, value in tags.items()}
    return {}


_COMMON = {
    ResourceType.JOB: _job_attributes,
    ResourceType.CLUSTER: _cluster_attributes,
    ResourceType.SQL_WAREHOUSE: _sql_warehouse_attributes,
    ResourceType.APP: _app_attributes,
    ResourceType.SERVING_ENDPOINT: _serving_endpoint_attributes,
    ResourceType.CATALOG: _catalog_attributes,
    ResourceType.SCHEMA: _schema_attributes,
    ResourceType.VOLUME: _volume_attributes,
    ResourceType.REGISTERED_MODEL: _registered_model_attributes,
    ResourceType.EXTERNAL_LOCATION: _external_location_attributes,
    ResourceType.SECRET_SCOPE: _secret_scope_attributes,
    ResourceType.QUALITY_MONITOR: _quality_monitor_attributes,
    ResourceType.PIPELINE: _pipeline_attributes,
    ResourceType.GENIE_SPACE: _genie_space_attributes,
    ResourceType.SQL_ALERT: _sql_alert_attributes,
}
