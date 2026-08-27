"""Tool implementations exposed over MCP.

Each function is a plain function of a `ServerContext` (or of nothing, for the static
catalog tools), so the whole surface is unit-testable without the MCP runtime. The FastMCP
layer in :mod:`policy_agent_mcp.server` registers each one as a tool. Every tool is
read-only; ``run_compliance_scan`` runs a live scan but persists nothing.
"""

from __future__ import annotations

from typing import Any

from policy_agent.policy import policy_to_dict, registered_operators
from policy_agent.policy.model import (
    RESOURCE_ATTRIBUTES,
    TAGGABLE_RESOURCE_TYPES,
    PolicyStatus,
    ResourceType,
)
from policy_agent.scan.engine import run_scan
from policy_agent.scan.registry import is_scannable
from policy_agent.scan.results import Finding, ScanResult
from policy_agent.storage.backend import load_policies, read_findings, read_scans

from policy_agent_mcp.context import ServerContext


def list_resource_types() -> list[dict[str, Any]]:
    """Returns every resource type a policy can target, with its attributes and capabilities.

    Returns:
        One entry per resource type with its ``resource_type`` value, whether it is
        ``scannable`` (has a live list API) and ``taggable``, and its sorted ``attributes``.
    """
    return [_resource_type_summary(resource_type) for resource_type in RESOURCE_ATTRIBUTES]


def describe_resource_type(resource_type: str) -> dict[str, Any]:
    """Returns the attributes and capabilities of a single resource type.

    Args:
        resource_type: A resource-type value such as ``job`` or ``sql_alert``.

    Returns:
        The resource type's summary (see :func:`list_resource_types`).

    Raises:
        ValueError: If ``resource_type`` is not a known resource type.
    """
    return _resource_type_summary(_parse_resource_type(resource_type))


def list_operators() -> list[str]:
    """Returns the comparison operators available for policy conditions.

    Returns:
        The registered operator names, sorted.
    """
    return sorted(registered_operators())


def list_policies(context: ServerContext, status: str | None = "approved") -> list[dict[str, Any]]:
    """Returns the stored policies, by default only the approved ones.

    Args:
        context: The server context.
        status: Approval status to filter by (``draft``, ``in_review``, ``approved``,
            ``rejected``, ``archived``); pass ``all`` or an empty value for every policy.

    Returns:
        The matching policies in canonical dictionary form.

    Raises:
        ValueError: If ``status`` is not a recognized status.
    """
    parsed = _parse_status(status)
    policies = load_policies(context.executor, context.config.storage, status=parsed)
    return [policy_to_dict(policy) for policy in policies]


def get_policy(context: ServerContext, name: str) -> dict[str, Any]:
    """Returns a single stored policy by name.

    Args:
        context: The server context.
        name: The policy name.

    Returns:
        The policy in canonical dictionary form.

    Raises:
        ValueError: If no policy with that name exists.
    """
    for policy in load_policies(context.executor, context.config.storage):
        if policy.name == name:
            return policy_to_dict(policy)
    raise ValueError(f"No policy named {name!r}.")


def run_compliance_scan(
    context: ServerContext,
    resource_types: list[str] | None = None,
    policy_names: list[str] | None = None,
) -> dict[str, Any]:
    """Runs a live compliance scan of the approved policies and returns the result.

    The scan reads the workspace but persists nothing, so it is safe to call repeatedly.

    Args:
        context: The server context.
        resource_types: Optional subset of resource-type values to scan; when omitted every
            resource type referenced by the selected policies is scanned.
        policy_names: Optional subset of approved policy names to evaluate; when omitted all
            approved policies are used.

    Returns:
        The scan id, timing, a summary, and the list of violations.

    Raises:
        ValueError: If a supplied resource type is not recognized.
    """
    policies = load_policies(context.executor, context.config.storage, status=PolicyStatus.APPROVED)
    if policy_names:
        wanted = set(policy_names)
        policies = [policy for policy in policies if policy.name in wanted]
    parsed_types = (
        [_parse_resource_type(value) for value in resource_types] if resource_types else None
    )
    result = run_scan(context.workspace_client, policies, parsed_types)
    return _scan_result_to_dict(result)


def list_recent_scans(context: ServerContext, limit: int = 20) -> list[dict[str, Any]]:
    """Returns recent persisted scan headers, most recent first.

    Args:
        context: The server context.
        limit: Maximum number of scans to return.

    Returns:
        Scan header rows (id, timing, counts) as column-keyed mappings.
    """
    scans = read_scans(context.executor, context.config.storage)
    return scans[: max(limit, 0)]


def get_scan_findings(context: ServerContext, scan_id: str) -> list[dict[str, Any]]:
    """Returns the findings recorded for a single persisted scan.

    Args:
        context: The server context.
        scan_id: The scan whose findings to return.

    Returns:
        One entry per finding evaluated in the scan.
    """
    findings = read_findings(context.executor, context.config.storage, scan_id)
    return [_finding_to_dict(finding) for finding in findings]


def _resource_type_summary(resource_type: ResourceType) -> dict[str, Any]:
    return {
        "resource_type": resource_type.value,
        "scannable": is_scannable(resource_type),
        "taggable": resource_type in TAGGABLE_RESOURCE_TYPES,
        "attributes": sorted(RESOURCE_ATTRIBUTES[resource_type]),
    }


def _parse_resource_type(value: str) -> ResourceType:
    try:
        return ResourceType(value)
    except ValueError as error:
        supported = ", ".join(sorted(rt.value for rt in RESOURCE_ATTRIBUTES))
        raise ValueError(
            f"Unknown resource type {value!r}. Supported resource types: {supported}."
        ) from error


def _parse_status(status: str | None) -> PolicyStatus | None:
    if status is None or status == "" or status.lower() == "all":
        return None
    try:
        return PolicyStatus(status)
    except ValueError as error:
        supported = ", ".join(member.value for member in PolicyStatus)
        raise ValueError(
            f"Unknown policy status {status!r}. Supported statuses: {supported}, all."
        ) from error


def _finding_to_dict(finding: Finding) -> dict[str, Any]:
    return {
        "policy_name": finding.policy_name,
        "resource_type": finding.resource_type.value,
        "resource_id": finding.resource_id,
        "resource_name": finding.resource_name,
        "compliant": finding.compliant,
        "enforcement_level": finding.enforcement_level.value,
        "message": finding.message,
        "remediation": finding.remediation,
        "owner": finding.owner,
    }


def _scan_result_to_dict(result: ScanResult) -> dict[str, Any]:
    summary = result.summary()
    return {
        "scan_id": result.scan_id,
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "summary": {
            "evaluated": summary.evaluated,
            "compliant": summary.compliant,
            "violations": summary.violations,
            "compliance_rate": summary.compliance_rate,
            "violations_by_enforcement_level": dict(summary.violations_by_enforcement_level),
            "violations_by_resource_type": dict(summary.violations_by_resource_type),
        },
        "violations": [_finding_to_dict(finding) for finding in result.violations],
    }
