"""Registry mapping each resource type to the function that fetches its snapshots.

Adding support for a new resource type is a one-line change here plus a ``scan_*`` function
in `policy_agent.scan.resources` and an attribute set in
`policy_agent.policy.model.RESOURCE_ATTRIBUTES`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from policy_agent.policy.model import ResourceType
from policy_agent.scan.resources import (
    scan_apps,
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
}
"""The resource types the framework can scan, keyed to their fetch functions. Some supported
resource types (e.g. quality monitors) have no list API and so are enforce-only, not scannable."""


def supported_resource_types() -> tuple[ResourceType, ...]:
    """Return every resource type that has a registered scanner.

    Returns:
        The supported resource types, in registration order.
    """
    return tuple(RESOURCE_SCANNERS)


def is_scannable(resource_type: ResourceType) -> bool:
    """Return whether a resource type can be live-scanned.

    Enforce-only types (those without a workspace list API, such as quality monitors) can still
    be evaluated from a bundle by the enforcement gate, but never by a live scan.

    Args:
        resource_type: The resource type to check.

    Returns:
        ``True`` if a scanner is registered for the resource type.
    """
    return resource_type in RESOURCE_SCANNERS


def scanner_for(resource_type: ResourceType) -> ResourceScanner:
    """Return the scanner function registered for a resource type.

    Args:
        resource_type: The resource type to look up.

    Returns:
        The function that fetches snapshots for the resource type.

    Raises:
        KeyError: If no scanner is registered for the resource type.
    """
    return RESOURCE_SCANNERS[resource_type]
