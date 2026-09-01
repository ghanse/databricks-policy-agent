"""Registry mapping each resource type to the function that fetches its snapshots.

Adding support for a new resource type is a one-line change here plus a ``scan_*`` function
in `policy_agent.scan.resources` and an attribute set in
`policy_agent.policy.model.RESOURCE_ATTRIBUTES`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from policy_agent.errors import UnsupportedResourceError
from policy_agent.policy.model import ResourceType
from policy_agent.scan.resources import (
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
from policy_agent.scan.results import ResourceSnapshot

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

ResourceScanner = Callable[["WorkspaceClient"], list[ResourceSnapshot]]

RESOURCE_SCANNERS: dict[ResourceType, ResourceScanner] = {
    ResourceType.JOB: scan_jobs,
    ResourceType.CLUSTER: scan_clusters,
    ResourceType.SQL_WAREHOUSE: scan_sql_warehouses,
    ResourceType.APP: scan_apps,
    ResourceType.SERVING_ENDPOINT: scan_serving_endpoints,
    ResourceType.CATALOG: scan_catalogs,
    ResourceType.SCHEMA: scan_schemas,
    ResourceType.VOLUME: scan_volumes,
    ResourceType.REGISTERED_MODEL: scan_registered_models,
    ResourceType.EXTERNAL_LOCATION: scan_external_locations,
    ResourceType.SECRET_SCOPE: scan_secret_scopes,
    ResourceType.PIPELINE: scan_pipelines,
    ResourceType.GENIE_SPACE: scan_genie_spaces,
    ResourceType.DATABASE_INSTANCE: scan_database_instances,
    ResourceType.SQL_ALERT: scan_sql_alerts,
    ResourceType.QUALITY_MONITOR: scan_quality_monitors,
}
"""The resource types the framework can scan, keyed to their fetch functions. A type without a
registered scanner is enforce-only — it can still be gated from a bundle but never live-scanned."""


def supported_resource_types() -> tuple[ResourceType, ...]:
    """Returns every resource type that has a registered scanner.

    Returns:
        The supported resource types, in registration order.
    """
    return tuple(RESOURCE_SCANNERS)


def is_scannable(resource_type: ResourceType) -> bool:
    """Return whether a resource type can be live-scanned.

    Enforce-only types (e.g. those without a workspace list API) can still be
    evaluated from a bundle by the enforcement gate, but never by a live scan.

    Args:
        resource_type: The resource type to check.

    Returns:
        *True* if a scanner is registered for the resource type.
    """
    return resource_type in RESOURCE_SCANNERS


def scanner_for(resource_type: ResourceType) -> ResourceScanner:
    """Returns the scanner function registered for a resource type.

    Args:
        resource_type: The resource type to look up.

    Returns:
        The function that fetches snapshots for the resource type.

    Raises:
        UnsupportedResourceError: If no scanner is registered for the resource type.
    """
    try:
        return RESOURCE_SCANNERS[resource_type]
    except KeyError as error:
        raise UnsupportedResourceError(
            f"No scanner is registered for resource type {resource_type.value!r}."
        ) from error
