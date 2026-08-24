"""Fetch workspace resources and normalize them into evaluable snapshots.

Each ``scan_*`` function reads one resource type from a :class:`WorkspaceClient` and maps
every resource to the flat attribute set declared in
:data:`policy_agent.policy.model.RESOURCE_ATTRIBUTES`. Missing SDK attributes degrade to
``None`` rather than raising, so a newer or older SDK still produces usable snapshots.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any

from policy_agent.policy.model import (
    OWNER_TYPE_SERVICE_PRINCIPAL,
    OWNER_TYPE_UNKNOWN,
    OWNER_TYPE_USER,
    ResourceType,
)
from policy_agent.scan.results import ResourceSnapshot

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

_HEX = "[0-9a-fA-F]"
_UUID_PATTERN = re.compile(rf"^{_HEX}{{8}}-{_HEX}{{4}}-{_HEX}{{4}}-{_HEX}{{4}}-{_HEX}{{12}}$")

TASK_DERIVED_JOB_ATTRIBUTES: frozenset[str] = frozenset(
    {"has_retry_policy", "uses_serverless_compute"}
)
"""Job attributes computed from a job's task definitions. Populating them requires listing
jobs with ``expand_tasks=True``, which fetches and deserializes every task — costly in large
workspaces — so callers should expand only when a policy actually reads one of these."""


def scan_jobs(
    workspace_client: WorkspaceClient, *, expand_tasks: bool = True
) -> list[ResourceSnapshot]:
    """Fetch and normalize every job in the workspace.

    Args:
        workspace_client: An authenticated Databricks workspace client.
        expand_tasks: Whether to fetch full task definitions. Required to populate the
            :data:`TASK_DERIVED_JOB_ATTRIBUTES`; when ``False`` those attributes are reported
            as ``None`` rather than a value guessed from tasks that were not fetched. Defaults
            to ``True`` so direct and inventory callers get complete snapshots.

    Returns:
        One snapshot per job.
    """
    snapshots = []
    for job in workspace_client.jobs.list(expand_tasks=expand_tasks):
        settings = job.settings
        owner, owner_type = _job_owner(job, getattr(settings, "run_as", None))
        schedule = getattr(settings, "schedule", None)
        snapshots.append(
            _snapshot(
                ResourceType.JOB,
                id=str(getattr(job, "job_id", "")),
                name=getattr(settings, "name", "") or "",
                owner=owner,
                owner_type=owner_type,
                tags=_normalize_tags(getattr(settings, "tags", None)),
                created_time=_epoch_seconds(getattr(job, "created_time", None)),
                schedule_pause_status=_enum_value(getattr(schedule, "pause_status", None)),
                max_concurrent_runs=getattr(settings, "max_concurrent_runs", None),
                timeout_seconds=getattr(settings, "timeout_seconds", None),
                run_as_type=owner_type,
                has_email_notifications=_has_failure_notifications(settings),
                has_retry_policy=_has_retry_policy(settings) if expand_tasks else None,
                uses_serverless_compute=(
                    _uses_serverless_compute(settings) if expand_tasks else None
                ),
                format=_enum_value(getattr(settings, "format", None)),
            )
        )
    return snapshots


def scan_clusters(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetch and normalize every all-purpose cluster in the workspace.

    Args:
        workspace_client: An authenticated Databricks workspace client.

    Returns:
        One snapshot per cluster.
    """
    snapshots = []
    for cluster in workspace_client.clusters.list():
        creator = getattr(cluster, "creator_user_name", None)
        snapshots.append(
            _snapshot(
                ResourceType.CLUSTER,
                id=str(getattr(cluster, "cluster_id", "")),
                name=getattr(cluster, "cluster_name", "") or "",
                owner=creator,
                owner_type=classify_principal(creator),
                tags=_normalize_tags(getattr(cluster, "custom_tags", None)),
                created_time=_epoch_seconds(getattr(cluster, "start_time", None)),
                cluster_source=_enum_value(getattr(cluster, "cluster_source", None)),
                autotermination_minutes=getattr(cluster, "autotermination_minutes", None),
                spark_version=getattr(cluster, "spark_version", None),
                node_type_id=getattr(cluster, "node_type_id", None),
                num_workers=getattr(cluster, "num_workers", None),
                data_security_mode=_enum_value(getattr(cluster, "data_security_mode", None)),
                single_user_name=getattr(cluster, "single_user_name", None),
            )
        )
    return snapshots


def scan_sql_warehouses(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetch and normalize every SQL warehouse in the workspace.

    Args:
        workspace_client: An authenticated Databricks workspace client.

    Returns:
        One snapshot per SQL warehouse.
    """
    snapshots = []
    for warehouse in workspace_client.warehouses.list():
        creator = getattr(warehouse, "creator_name", None)
        snapshots.append(
            _snapshot(
                ResourceType.SQL_WAREHOUSE,
                id=str(getattr(warehouse, "id", "")),
                name=getattr(warehouse, "name", "") or "",
                owner=creator,
                owner_type=classify_principal(creator),
                tags=_normalize_tags(getattr(warehouse, "tags", None)),
                created_time=None,
                warehouse_type=_enum_value(getattr(warehouse, "warehouse_type", None)),
                cluster_size=getattr(warehouse, "cluster_size", None),
                auto_stop_minutes=getattr(warehouse, "auto_stop_mins", None),
                enable_serverless_compute=getattr(warehouse, "enable_serverless_compute", None),
                min_num_clusters=getattr(warehouse, "min_num_clusters", None),
                max_num_clusters=getattr(warehouse, "max_num_clusters", None),
            )
        )
    return snapshots


def scan_apps(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetch and normalize every Databricks App in the workspace.

    Args:
        workspace_client: An authenticated Databricks workspace client.

    Returns:
        One snapshot per app.
    """
    snapshots = []
    for app in workspace_client.apps.list():
        creator = getattr(app, "creator", None)
        name = getattr(app, "name", "") or ""
        active_deployment = getattr(app, "active_deployment", None)
        snapshots.append(
            _snapshot(
                ResourceType.APP,
                id=name,
                name=name,
                owner=creator,
                owner_type=classify_principal(creator),
                tags={},
                created_time=_rfc3339_seconds(getattr(app, "create_time", None)),
                app_status=_enum_value(getattr(getattr(app, "app_status", None), "state", None)),
                compute_status=_enum_value(
                    getattr(getattr(app, "compute_status", None), "state", None)
                ),
                active_deployment_mode=_enum_value(getattr(active_deployment, "mode", None)),
            )
        )
    return snapshots


def scan_serving_endpoints(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetch and normalize every model serving endpoint in the workspace.

    Args:
        workspace_client: An authenticated Databricks workspace client.

    Returns:
        One snapshot per serving endpoint.
    """
    snapshots = []
    for endpoint in workspace_client.serving_endpoints.list():
        creator = getattr(endpoint, "creator", None)
        name = getattr(endpoint, "name", "") or ""
        state = getattr(endpoint, "state", None)
        snapshots.append(
            _snapshot(
                ResourceType.SERVING_ENDPOINT,
                id=str(getattr(endpoint, "id", None) or name),
                name=name,
                owner=creator,
                owner_type=classify_principal(creator),
                tags=_normalize_tags(getattr(endpoint, "tags", None)),
                created_time=_epoch_seconds(getattr(endpoint, "creation_timestamp", None)),
                endpoint_state=_enum_value(getattr(state, "ready", None)),
                endpoint_type=_enum_value(getattr(endpoint, "endpoint_type", None)),
                budget_policy_id=getattr(endpoint, "budget_policy_id", None),
                route_optimized=getattr(endpoint, "route_optimized", None),
            )
        )
    return snapshots


def classify_principal(identifier: str | None) -> str:
    """Classify a principal identifier as a service principal, user, or unknown.

    Args:
        identifier: A principal identifier such as a user email or SP application id.

    Returns:
        One of the ``OWNER_TYPE_*`` constants.
    """
    if not identifier:
        return OWNER_TYPE_UNKNOWN
    if _UUID_PATTERN.match(identifier):
        return OWNER_TYPE_SERVICE_PRINCIPAL
    if "@" in identifier:
        return OWNER_TYPE_USER
    return OWNER_TYPE_UNKNOWN


def _snapshot(resource_type: ResourceType, **attributes: Any) -> ResourceSnapshot:
    return ResourceSnapshot(resource_type=resource_type, attributes=attributes)


def _job_owner(job: Any, run_as: Any) -> tuple[str | None, str]:
    if run_as is not None:
        service_principal = getattr(run_as, "service_principal_name", None)
        if service_principal:
            return service_principal, OWNER_TYPE_SERVICE_PRINCIPAL
        user = getattr(run_as, "user_name", None)
        if user:
            return user, classify_principal(user)
    creator = getattr(job, "creator_user_name", None)
    return creator, classify_principal(creator)


def _has_failure_notifications(settings: Any) -> bool:
    notifications = getattr(settings, "email_notifications", None)
    on_failure = getattr(notifications, "on_failure", None)
    return bool(on_failure)


def _has_retry_policy(settings: Any) -> bool:
    tasks = getattr(settings, "tasks", None)
    if not tasks:
        return False
    return all(_task_has_retries(task) for task in tasks)


def _task_has_retries(task: Any) -> bool:
    max_retries = getattr(task, "max_retries", None)
    # A task retries when max_retries is a nonzero count; -1 means unlimited, 0 means never.
    return (
        isinstance(max_retries, int)
        and not isinstance(max_retries, bool)
        and (max_retries == -1 or max_retries > 0)
    )


def _uses_serverless_compute(settings: Any) -> bool:
    tasks = getattr(settings, "tasks", None)
    if not tasks:
        return False
    return all(_task_is_serverless(task) for task in tasks)


def _task_is_serverless(task: Any) -> bool:
    # A serverless task references no classic compute: no interactive cluster, no
    # task-defined job cluster, and no shared job-cluster key.
    return (
        getattr(task, "existing_cluster_id", None) is None
        and getattr(task, "new_cluster", None) is None
        and getattr(task, "job_cluster_key", None) is None
    )


def _normalize_tags(raw: Any) -> dict[str, str]:
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return {str(key): str(value) for key, value in raw.items()}
    pairs = getattr(raw, "custom_tags", raw)
    result: dict[str, str] = {}
    if isinstance(pairs, list | tuple):
        for item in pairs:
            key = getattr(item, "key", None)
            if key is not None:
                value = getattr(item, "value", None)
                result[str(key)] = "" if value is None else str(value)
    return result


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _epoch_seconds(milliseconds: Any) -> int | None:
    if not isinstance(milliseconds, int | float) or isinstance(milliseconds, bool):
        return None
    return int(milliseconds // 1000)


def _rfc3339_seconds(timestamp: Any) -> int | None:
    if not isinstance(timestamp, str) or not timestamp:
        return None
    try:
        return int(datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None
