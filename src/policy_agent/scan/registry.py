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
    scan_clusters,
    scan_genie_spaces,
    scan_jobs,
    scan_serving_endpoints,
    scan_sql_warehouses,
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
    ResourceType.GENIE_SPACE: scan_genie_spaces,
}
"""The resource types the framework can scan, keyed to their fetch functions."""


def supported_resource_types() -> tuple[ResourceType, ...]:
    """Returns every resource type that has a registered scanner.

    Returns:
        The supported resource types, in registration order.
    """
    return tuple(RESOURCE_SCANNERS)


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
