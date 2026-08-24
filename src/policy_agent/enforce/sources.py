"""Map a resolved bundle configuration into evaluable resource snapshots.

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
    "apps": ResourceType.APP,
    "model_serving_endpoints": ResourceType.SERVING_ENDPOINT,
}


def snapshot_bundle(config: dict[str, Any]) -> list[ResourceSnapshot]:
    """Build resource snapshots from a resolved bundle configuration.

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
    return {
        **_common(key, definition.get("name"), owner, owner_type, definition.get("tags")),
        "schedule_pause_status": schedule.get("pause_status"),
        "max_concurrent_runs": definition.get("max_concurrent_runs"),
        "timeout_seconds": definition.get("timeout_seconds"),
        "run_as_type": owner_type,
        "has_email_notifications": bool(notifications.get("on_failure")),
        "format": definition.get("format"),
    }


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


def _app_attributes(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        **_common(key, definition.get("name"), None, OWNER_TYPE_UNKNOWN, None),
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
        return {str(key): str(value) for key, value in tags.items()}
    return {}


_COMMON = {
    ResourceType.JOB: _job_attributes,
    ResourceType.CLUSTER: _cluster_attributes,
    ResourceType.APP: _app_attributes,
    ResourceType.SERVING_ENDPOINT: _serving_endpoint_attributes,
}
