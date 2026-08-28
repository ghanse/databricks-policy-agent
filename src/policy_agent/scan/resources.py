"""Fetches workspace resources and normalizes them into evaluable snapshots.

Each ``scan_*`` function reads one resource type from a `WorkspaceClient` and maps
every resource to the flat attribute set declared in
`policy_agent.policy.model.RESOURCE_ATTRIBUTES`. Missing SDK attributes degrade to
``None`` rather than raising, so a newer or older SDK still produces usable snapshots.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any

from policy_agent.errors import UnsupportedResourceError
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
    """Fetches and normalizes every job in the workspace.

    Args:
        workspace_client: Databricks workspace client.
        expand_tasks: Whether to fetch full task definitions. Required to populate the
            `TASK_DERIVED_JOB_ATTRIBUTES`; when *False* those attributes are reported
            as *None* rather than a value guessed from tasks that were not fetched. Defaults
            to *True* so direct and inventory callers get complete snapshots.

    Returns:
        A list of *ResourceSnapshots* for each job.
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
    """Fetches and normalizes every all-purpose cluster in the workspace.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each cluster.
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
    """Fetches and normalizes every SQL warehouse in the workspace.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each SQL warehouse.
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
    """Fetches and normalizes every Databricks App in the workspace.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each app.
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
                tags=_get_entity_tags(workspace_client, "apps", name),
                created_time=_rfc3339_seconds(getattr(app, "create_time", None)),
                app_status=_enum_value(getattr(getattr(app, "app_status", None), "state", None)),
                compute_status=_enum_value(
                    getattr(getattr(app, "compute_status", None), "state", None)
                ),
                active_deployment_mode=_enum_value(getattr(active_deployment, "mode", None)),
            )
        )
    return snapshots


def _get_entity_tags(
    workspace_client: WorkspaceClient, entity_type: str, entity_id: str
) -> dict[str, str]:
    """Fetches an entity's workspace tag assignments as a flat key-value mapping.

    Used for resource types whose tags are governed through the workspace entity-tag-assignments
    API (e.g. Databricks Apps and Genie spaces).

    Args:
        workspace_client: Databricks workspace client.
        entity_type: The tag-assignment entity type (e.g. *apps* or *geniespaces*).
        entity_id: The entity's identifier (e.g. the app name or Genie space id).

    Returns:
        A mapping of tag key to tag value; empty when the entity has no tags or the SDK does not
        expose the entity-tag-assignments API.
    """
    tag_service = getattr(workspace_client, "workspace_entity_tag_assignments", None)
    if tag_service is None or not entity_id:
        return {}
    tags: dict[str, str] = {}
    for assignment in tag_service.list_tag_assignments(
        entity_type=entity_type, entity_id=entity_id
    ):
        key = getattr(assignment, "tag_key", None)
        if key is not None:
            tags[str(key)] = str(getattr(assignment, "tag_value", "") or "")
    return tags


def _get_uc_entity_tags(
    workspace_client: WorkspaceClient, entity_type: str, entity_name: str
) -> dict[str, str]:
    """Fetches a Unity Catalog securable's tag assignments as a flat key-value mapping.

    Unity Catalog securables (e.g. catalogs, schemas, volumes, external locations) are tagged
    through the entity-tag-assignments API, which uses fully-qualified securable names.

    Args:
        workspace_client: Databricks workspace client.
        entity_type: The UC tag-assignment entity type (e.g. *catalogs* or *externallocations*).
        entity_name: The securable's fully-qualified name.

    Returns:
        A mapping of tag key to tag value; empty when the securable has no tags or the SDK does
        not expose the UC entity-tag-assignments API.
    """
    tag_service = getattr(workspace_client, "entity_tag_assignments", None)
    if tag_service is None or not entity_name:
        return {}
    tags: dict[str, str] = {}
    for assignment in tag_service.list(entity_type=entity_type, entity_name=entity_name):
        key = getattr(assignment, "tag_key", None)
        if key is not None:
            tags[str(key)] = str(getattr(assignment, "tag_value", "") or "")
    return tags


def scan_serving_endpoints(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every model serving endpoint in the workspace.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each serving endpoint.
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


def scan_catalogs(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every catalog in the workspace's metastore.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each catalog.
    """
    snapshots = []
    for catalog in workspace_client.catalogs.list():
        owner = getattr(catalog, "owner", None)
        name = getattr(catalog, "name", "") or ""
        snapshots.append(
            _snapshot(
                ResourceType.CATALOG,
                id=name,
                name=name,
                owner=owner,
                owner_type=classify_principal(owner),
                tags=_get_uc_entity_tags(workspace_client, "catalogs", name),
                created_time=_epoch_seconds(getattr(catalog, "created_at", None)),
                comment=getattr(catalog, "comment", None),
                catalog_type=_enum_value(getattr(catalog, "catalog_type", None)),
                isolation_mode=_enum_value(getattr(catalog, "isolation_mode", None)),
                storage_root=getattr(catalog, "storage_root", None),
            )
        )
    return snapshots


def scan_schemas(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every schema across every catalog in the metastore.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each schema.
    """
    snapshots = []
    for catalog in workspace_client.catalogs.list():
        catalog_name = getattr(catalog, "name", None)
        if not catalog_name:
            continue
        for schema in workspace_client.schemas.list(catalog_name=catalog_name):
            owner = getattr(schema, "owner", None)
            name = getattr(schema, "name", "") or ""
            full_name = getattr(schema, "full_name", None) or f"{catalog_name}.{name}"
            snapshots.append(
                _snapshot(
                    ResourceType.SCHEMA,
                    id=full_name,
                    name=name,
                    owner=owner,
                    owner_type=classify_principal(owner),
                    tags=_get_uc_entity_tags(workspace_client, "schemas", full_name),
                    created_time=_epoch_seconds(getattr(schema, "created_at", None)),
                    comment=getattr(schema, "comment", None),
                    catalog_name=catalog_name,
                )
            )
    return snapshots


def scan_volumes(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every volume across every schema in the metastore.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each volume.
    """
    snapshots = []
    for catalog in workspace_client.catalogs.list():
        catalog_name = getattr(catalog, "name", None)
        if not catalog_name:
            continue
        for schema in workspace_client.schemas.list(catalog_name=catalog_name):
            schema_name = getattr(schema, "name", None)
            if not schema_name:
                continue
            for volume in workspace_client.volumes.list(
                catalog_name=catalog_name, schema_name=schema_name
            ):
                owner = getattr(volume, "owner", None)
                name = getattr(volume, "name", "") or ""
                full_name = (
                    getattr(volume, "full_name", None) or f"{catalog_name}.{schema_name}.{name}"
                )
                snapshots.append(
                    _snapshot(
                        ResourceType.VOLUME,
                        id=full_name,
                        name=name,
                        owner=owner,
                        owner_type=classify_principal(owner),
                        tags=_get_uc_entity_tags(workspace_client, "volumes", full_name),
                        created_time=_epoch_seconds(getattr(volume, "created_at", None)),
                        comment=getattr(volume, "comment", None),
                        catalog_name=catalog_name,
                        schema_name=schema_name,
                        volume_type=_enum_value(getattr(volume, "volume_type", None)),
                    )
                )
    return snapshots


def scan_registered_models(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every Unity Catalog registered model in the metastore.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each registered model.
    """
    snapshots = []
    for model in workspace_client.registered_models.list():
        owner = getattr(model, "owner", None)
        name = getattr(model, "name", "") or ""
        snapshots.append(
            _snapshot(
                ResourceType.REGISTERED_MODEL,
                id=getattr(model, "full_name", None) or name,
                name=name,
                owner=owner,
                owner_type=classify_principal(owner),
                created_time=_epoch_seconds(getattr(model, "created_at", None)),
                comment=getattr(model, "comment", None),
                catalog_name=getattr(model, "catalog_name", None),
                schema_name=getattr(model, "schema_name", None),
            )
        )
    return snapshots


def scan_pipelines(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every Spark Declarative pipeline in the workspace.

    Note:
        *list_pipelines* returns only summary attributes (e.g. name, creator, state). Because
        some attributes (e.g. catalog, edition, continuous, serverless) are part of the pipeline
        spec, each pipeline is fetched with *get* to read its attributes.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each serving endpoint.
    """
    snapshots = []
    for pipeline in workspace_client.pipelines.list_pipelines():
        pipeline_id = getattr(pipeline, "pipeline_id", "") or ""
        creator = getattr(pipeline, "creator_user_name", None)
        spec = None
        if pipeline_id:
            spec = getattr(workspace_client.pipelines.get(pipeline_id), "spec", None)
        snapshots.append(
            _snapshot(
                ResourceType.PIPELINE,
                id=str(pipeline_id),
                name=getattr(pipeline, "name", None) or getattr(spec, "name", "") or "",
                owner=creator,
                owner_type=classify_principal(creator),
                tags=_normalize_tags(getattr(spec, "tags", None)),
                created_time=None,
                catalog=getattr(spec, "catalog", None),
                target=getattr(spec, "target", None),
                schema=getattr(spec, "schema", None),
                channel=getattr(spec, "channel", None),
                edition=getattr(spec, "edition", None),
                continuous=getattr(spec, "continuous", None),
                photon=getattr(spec, "photon", None),
                serverless=getattr(spec, "serverless", None),
                development=getattr(spec, "development", None),
            )
        )
    return snapshots


def scan_external_locations(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every external location in the metastore.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each external location.
    """
    snapshots = []
    for location in workspace_client.external_locations.list():
        owner = getattr(location, "owner", None)
        name = getattr(location, "name", "") or ""
        snapshots.append(
            _snapshot(
                ResourceType.EXTERNAL_LOCATION,
                id=name,
                name=name,
                owner=owner,
                owner_type=classify_principal(owner),
                tags=_get_uc_entity_tags(workspace_client, "externallocations", name),
                created_time=_epoch_seconds(getattr(location, "created_at", None)),
                comment=getattr(location, "comment", None),
                url=getattr(location, "url", None),
                credential_name=getattr(location, "credential_name", None),
                read_only=getattr(location, "read_only", None),
                isolation_mode=_enum_value(getattr(location, "isolation_mode", None)),
            )
        )
    return snapshots


def scan_secret_scopes(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every secret scope in the workspace.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each secret scope.
    """
    snapshots = []
    for scope in workspace_client.secrets.list_scopes():
        name = getattr(scope, "name", "") or ""
        snapshots.append(
            _snapshot(
                ResourceType.SECRET_SCOPE,
                id=name,
                name=name,
                backend_type=_enum_value(getattr(scope, "backend_type", None)),
            )
        )
    return snapshots


def scan_genie_spaces(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every Genie space in the workspace.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each Genie space.
    """
    snapshots = []
    page_token: str | None = None
    genie_client = getattr(workspace_client, "genie", None)
    if not genie_client:
        from databricks.sdk import version as databricks_sdk_version

        raise UnsupportedResourceError(
            f"Databricks SDK version {databricks_sdk_version.__version__} does not provide the "
            "'genie' API. Upgrade the Databricks SDK to scan Genie spaces."
        )
    while True:
        response = genie_client.list_spaces(page_token=page_token)
        for space in getattr(response, "spaces", None) or []:
            title = getattr(space, "title", "") or ""
            description = getattr(space, "description", None)
            space_id = str(getattr(space, "space_id", ""))
            snapshots.append(
                _snapshot(
                    ResourceType.GENIE_SPACE,
                    id=space_id,
                    name=title,
                    tags=_get_entity_tags(workspace_client, "geniespaces", space_id),
                    warehouse_id=getattr(space, "warehouse_id", None),
                    description=description,
                    has_description=bool(description),
                )
            )
        page_token = getattr(response, "next_page_token", None)
        if not page_token:
            return snapshots


def scan_quality_monitors(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]:
    """Fetches and normalizes every data-profiling (Lakehouse Monitoring) quality monitor.

    Note:
        Uses the data-quality API (*data_quality.list_monitor*); each monitor's classic
        Lakehouse Monitoring settings live in its *data_profiling_config*. Monitors that carry
        no data-profiling config (for example anomaly-detection-only monitors) are skipped
        because they do not map to this resource type's attributes. Older SDKs without the
        *data_quality* API raise `UnsupportedResourceError`.

    Args:
        workspace_client: Databricks workspace client.

    Returns:
        A list of *ResourceSnapshots* for each data-profiling quality monitor.
    """
    data_quality = getattr(workspace_client, "data_quality", None)
    if not data_quality:
        from databricks.sdk import version as databricks_sdk_version

        raise UnsupportedResourceError(
            f"Databricks SDK version {databricks_sdk_version.__version__} does not provide the "
            "'data_quality' API. Upgrade the Databricks SDK to scan quality monitors."
        )
    snapshots = []
    for monitor in data_quality.list_monitor():
        profiling = getattr(monitor, "data_profiling_config", None)
        if profiling is None:
            continue
        table_name = getattr(profiling, "monitored_table_name", None)
        snapshots.append(
            _snapshot(
                ResourceType.QUALITY_MONITOR,
                id=table_name or str(getattr(monitor, "object_id", "") or ""),
                name=table_name or "",
                table_name=table_name,
                output_schema_name=getattr(profiling, "output_schema_id", None),
                monitor_type=_profiling_monitor_type(profiling),
                has_schedule=bool(getattr(profiling, "schedule", None)),
            )
        )
    return snapshots


def _profiling_monitor_type(profiling: Any) -> str | None:
    # A data-profiling config sets exactly one of these profile blocks; mirror the bundle
    # reader so a scanned and a bundle-declared monitor report the same monitor_type.
    for kind in ("snapshot", "time_series", "inference_log"):
        if getattr(profiling, kind, None) is not None:
            return kind
    return None


def classify_principal(identifier: str | None) -> str:
    """Classifies a principal identifier as a service principal, user, or unknown.

    Args:
        identifier: A principal identifier such as a user email or application id.

    Returns:
        One of the ``OWNER_TYPE_*`` constants: ``service_principal`` for a UUID, ``user`` for an
        email-shaped value, and ``unknown`` for an empty identifier or any other value.
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
