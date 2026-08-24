"""The scan orchestrator — the primary public entry point for running compliance scans.

``run_scan`` fetches each relevant resource type once, evaluates every applicable policy
against every resource, and returns an immutable :class:`ScanResult`. It is a pure function
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
from policy_agent.scan.registry import scanner_for
from policy_agent.scan.resources import TASK_DERIVED_JOB_ATTRIBUTES, scan_jobs
from policy_agent.scan.results import Finding, ResourceSnapshot, ScanResult

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient


def run_scan(
    workspace_client: WorkspaceClient,
    policies: Iterable[Policy],
    resource_types: Iterable[ResourceType] | None = None,
) -> ScanResult:
    """Scan the workspace for compliance with the given policies.

    Only resource types that both appear in ``policies`` and (when provided) in
    ``resource_types`` are fetched, so a scan never calls an API it does not need.

    Args:
        workspace_client: An authenticated Databricks workspace client.
        policies: The policies to evaluate. Each is validated before use.
        resource_types: Optional restriction on which resource types to scan; when ``None``
            every resource type referenced by ``policies`` is scanned.

    Returns:
        A :class:`ScanResult` containing one finding per applicable (policy, resource) pair.

    Raises:
        InvalidPolicyError: If any supplied policy fails validation.
        UnknownConditionError: If any policy references an unregistered operator.
    """
    policy_list = list(policies)
    for policy in policy_list:
        validate_policy(policy)

    policies_by_type = _group_by_resource_type(policy_list)
    requested = set(resource_types) if resource_types is not None else set(policies_by_type)
    types_to_scan = [rt for rt in policies_by_type if rt in requested]

    started_at = datetime.now(UTC)
    findings: list[Finding] = []
    for resource_type in types_to_scan:
        snapshots = _fetch_snapshots(
            workspace_client, resource_type, policies_by_type[resource_type]
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
    """Fetch resource snapshots without evaluating any policy.

    Useful for inventory views and dry runs where only the normalized resource attributes
    are needed.

    Args:
        workspace_client: An authenticated Databricks workspace client.
        resource_types: The resource types to fetch.

    Returns:
        A mapping from each requested resource type to its snapshots.
    """
    return {
        resource_type: scanner_for(resource_type)(workspace_client)
        for resource_type in resource_types
    }


def _fetch_snapshots(
    workspace_client: WorkspaceClient,
    resource_type: ResourceType,
    policies: list[Policy],
) -> list[ResourceSnapshot]:
    """Fetch snapshots for one resource type, fetching only the data its policies need.

    Jobs are the one type with an expensive optional expansion: task definitions are fetched
    only when a policy reads a task-derived attribute (retry policy or serverless compute).
    Every other type has a single, uniform scanner.
    """
    if resource_type is ResourceType.JOB:
        referenced: set[str] = set()
        for policy in policies:
            referenced |= referenced_attributes(policy)
        expand_tasks = bool(referenced & TASK_DERIVED_JOB_ATTRIBUTES)
        return scan_jobs(workspace_client, expand_tasks=expand_tasks)
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
