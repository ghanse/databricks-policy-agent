"""The scan orchestrator — the primary public entry point for running compliance scans.

``run_scan`` fetches each relevant resource type once, evaluates every applicable policy
against every resource, and returns an immutable `ScanResult`. It is a pure function
of the workspace state and the supplied policies, which makes it equally usable from ad-hoc
code, a scheduled job, or the app's API.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from policy_agent.policy.model import Policy, ResourceType, referenced_attributes
from policy_agent.policy.validation import validate_policy
from policy_agent.scan.evaluator import evaluate_resource
from policy_agent.scan.registry import is_scannable, scanner_for
from policy_agent.scan.resources import (
    TASK_DERIVED_JOB_ATTRIBUTES,
    ScanCache,
    scan_columns,
    scan_jobs,
    scan_notebooks,
    scan_tables,
    scan_workspace_files,
)
from policy_agent.scan.results import Finding, ResourceSnapshot, ScanResult

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient


def run_scan(
    workspace_client: WorkspaceClient,
    policies: Iterable[Policy],
    resource_types: Iterable[ResourceType] | None = None,
) -> ScanResult:
    """Scans the workspace for compliance with the given policies.

    Only resource types that both appear in ``policies`` and (when provided) in
    ``resource_types`` are fetched, so a scan never calls an API it does not need.

    Args:
        workspace_client: An authenticated Databricks workspace client.
        policies: The policies to evaluate. Each is validated before use.
        resource_types: Optional restriction on which resource types to scan; when ``None``
            every resource type referenced by ``policies`` is scanned.

    Returns:
        A `ScanResult` containing one finding per applicable (policy, resource) pair.

    Raises:
        InvalidPolicyError: If any supplied policy fails validation.
        UnknownConditionError: If any policy references an unregistered operator.
    """
    policy_list = list(policies)
    for policy in policy_list:
        validate_policy(policy)

    policies_by_type = _group_by_resource_type(policy_list)
    requested = set(resource_types) if resource_types is not None else set(policies_by_type)
    # Enforce-only types (any without a registered scanner) are validated and can be gated
    # from a bundle, but are silently skipped by a live scan since they cannot be fetched.
    types_to_scan = [rt for rt in policies_by_type if rt in requested and is_scannable(rt)]

    started_at = datetime.now(UTC)
    cache = ScanCache()
    findings: list[Finding] = []
    for resource_type in types_to_scan:
        snapshots = _fetch_snapshots(
            workspace_client, resource_type, policies_by_type[resource_type], cache
        )
        findings.extend(_evaluate_type(policies_by_type[resource_type], snapshots))
    finished_at = datetime.now(UTC)

    return ScanResult(
        scan_id=uuid.uuid4().hex,
        started_at=started_at,
        finished_at=finished_at,
        findings=tuple(findings),
        policy_names=tuple(policy.name for policy in policy_list),
        resource_types=tuple(types_to_scan),
    )


def collect_snapshots(
    workspace_client: WorkspaceClient,
    resource_types: Iterable[ResourceType],
) -> dict[ResourceType, list[ResourceSnapshot]]:
    """Fetches resource snapshots without evaluating any policy.

    Useful for inventory views and dry runs where only the normalized resource attributes
    are needed.

    Args:
        workspace_client: An authenticated Databricks workspace client.
        resource_types: The resource types to fetch.

    Returns:
        A mapping from each requested resource type to its snapshots.
    """
    cache = ScanCache()
    return {
        resource_type: _scan_type(workspace_client, resource_type, cache)
        for resource_type in resource_types
    }


def _fetch_snapshots(
    workspace_client: WorkspaceClient,
    resource_type: ResourceType,
    policies: list[Policy],
    cache: ScanCache,
) -> list[ResourceSnapshot]:
    """Fetches snapshots for one resource type, fetching only the data its policies need.

    Some types have an expensive optional fetch that is done only when a policy reads an attribute
    that needs it: jobs fetch task definitions for the task-derived attributes, and tables and
    columns fetch their governed tags (one entity-tag API call per resource). Every other type has
    a single, uniform scanner.
    """
    if resource_type is ResourceType.JOB:
        referenced = _referenced_attributes(policies)
        expand_tasks = bool(referenced & TASK_DERIVED_JOB_ATTRIBUTES)
        return scan_jobs(workspace_client, expand_tasks=expand_tasks)
    if resource_type is ResourceType.TABLE:
        fetch_tags = "tags" in _referenced_attributes(policies)
        return scan_tables(workspace_client, cache=cache, fetch_tags=fetch_tags)
    if resource_type is ResourceType.COLUMN:
        fetch_tags = "tags" in _referenced_attributes(policies)
        return scan_columns(workspace_client, cache=cache, fetch_tags=fetch_tags)
    return _scan_type(workspace_client, resource_type, cache)


def _referenced_attributes(policies: list[Policy]) -> set[str]:
    referenced: set[str] = set()
    for policy in policies:
        referenced |= referenced_attributes(policy)
    return referenced


def _scan_type(
    workspace_client: WorkspaceClient, resource_type: ResourceType, cache: ScanCache
) -> list[ResourceSnapshot]:
    """Runs one type's scanner, passing the shared cache to the scanners that can reuse it.

    Tables and columns derive from the same metastore walk, and notebooks and workspace files
    from the same workspace tree walk, so those four take the per-scan cache and list only once
    when both types of a pair are scanned. Every other scanner is a plain function of the
    workspace client.
    """
    if resource_type is ResourceType.TABLE:
        return scan_tables(workspace_client, cache=cache)
    if resource_type is ResourceType.COLUMN:
        return scan_columns(workspace_client, cache=cache)
    if resource_type is ResourceType.NOTEBOOK:
        return scan_notebooks(workspace_client, cache=cache)
    if resource_type is ResourceType.WORKSPACE_FILE:
        return scan_workspace_files(workspace_client, cache=cache)
    return scanner_for(resource_type)(workspace_client)


def _group_by_resource_type(policies: list[Policy]) -> dict[ResourceType, list[Policy]]:
    grouped: dict[ResourceType, list[Policy]] = defaultdict(list)
    for policy in policies:
        grouped[policy.resource_type].append(policy)
    return grouped


def _evaluate_type(policies: list[Policy], snapshots: list[ResourceSnapshot]) -> list[Finding]:
    findings: list[Finding] = []
    for snapshot in snapshots:
        for policy in policies:
            finding = evaluate_resource(policy, snapshot)
            if finding is not None:
                findings.append(finding)
    return findings
