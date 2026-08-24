"""Conversions between domain objects and storage rows.

Rows are plain ``dict`` mappings keyed by column name. Readers coerce values defensively
because the Delta backend returns every column as a string while the Lakebase backend
returns native Python types; both must round-trip through the same reader.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from policy_agent.approval.roles import Role
from policy_agent.approval.workflow import ApprovalEvent
from policy_agent.policy.model import Effect, EnforcementLevel, Policy, PolicyStatus, ResourceType
from policy_agent.policy.serialization import (
    condition_from_dict,
    condition_to_dict,
    policy_to_dict,
)
from policy_agent.remediation.model import RemediationItem, RemediationStatus
from policy_agent.scan.results import Finding, ScanResult
from policy_agent.schedule import ScanSchedule
from policy_agent.storage.config import StorageConfig


def policy_to_row(policy: Policy, config: StorageConfig, updated_at: datetime) -> dict[str, Any]:
    """Serialise a policy to a ``policies`` row.

    Args:
        policy: The policy to serialise.
        config: Storage config supplying object tags.
        updated_at: Timestamp recorded on the row.

    Returns:
        A row mapping ready for insertion.
    """
    return {
        "name": policy.name,
        "resource_type": policy.resource_type.value,
        "effect": policy.effect.value,
        "enforcement": policy.enforcement.value,
        "status": policy.status.value,
        "version": policy.version,
        "description": policy.description,
        "remediation": policy.remediation,
        "rule": json.dumps(condition_to_dict(policy.rule)),
        "match": json.dumps(condition_to_dict(policy.match)) if policy.match is not None else None,
        "object_tags": _object_tags(config),
        "updated_at": updated_at,
    }


def row_to_policy(row: dict[str, Any]) -> Policy:
    """Deserialise a ``policies`` row into a policy.

    Args:
        row: The row mapping read from storage.

    Returns:
        The reconstructed policy.
    """
    match = _loads(row.get("match"))
    return Policy(
        name=str(row["name"]),
        resource_type=ResourceType(row["resource_type"]),
        effect=Effect(row["effect"]),
        rule=condition_from_dict(_loads(row["rule"])),
        description=_as_str(row.get("description")) or "",
        enforcement=EnforcementLevel(row["enforcement"]),
        match=condition_from_dict(match) if match is not None else None,
        remediation=_as_str(row.get("remediation")) or "",
        status=PolicyStatus(row["status"]),
        version=_as_int(row.get("version")) or 1,
    )


def policy_version_to_row(policy: Policy, actor: str, created_at: datetime) -> dict[str, Any]:
    """Serialise a snapshot of a policy to a ``policy_versions`` row.

    Args:
        policy: The policy being versioned.
        actor: The principal who created this version.
        created_at: Timestamp recorded on the row.

    Returns:
        A row mapping ready for insertion.
    """
    return {
        "name": policy.name,
        "version": policy.version,
        "definition": json.dumps(policy_to_dict(policy)),
        "actor": actor,
        "created_at": created_at,
    }


def scan_to_row(
    scan_result: ScanResult, config: StorageConfig, triggered_by: str
) -> dict[str, Any]:
    """Serialise a scan result's header to a ``scans`` row.

    Args:
        scan_result: The completed scan result.
        config: Storage config supplying object tags.
        triggered_by: Principal or process that initiated the scan.

    Returns:
        A row mapping ready for insertion.
    """
    summary = scan_result.summary()
    return {
        "scan_id": scan_result.scan_id,
        "started_at": scan_result.started_at,
        "finished_at": scan_result.finished_at,
        "policy_names": json.dumps(list(scan_result.policy_names)),
        "resource_types": json.dumps([rt.value for rt in scan_result.resource_types]),
        "evaluated": summary.evaluated,
        "compliant": summary.compliant,
        "violations": summary.violations,
        "summary": json.dumps(
            {
                "by_enforcement": dict(summary.violations_by_enforcement),
                "by_resource_type": dict(summary.violations_by_resource_type),
                "compliance_rate": summary.compliance_rate,
            }
        ),
        "triggered_by": triggered_by,
        "object_tags": _object_tags(config),
    }


def finding_to_row(
    finding: Finding, scan_id: str, config: StorageConfig, created_at: datetime
) -> dict[str, Any]:
    """Serialise a finding to a ``findings`` row.

    Args:
        finding: The finding to serialise.
        scan_id: Identifier of the scan that produced the finding.
        config: Storage config supplying object tags.
        created_at: Timestamp recorded on the row.

    Returns:
        A row mapping ready for insertion.
    """
    return {
        "finding_id": uuid.uuid4().hex,
        "scan_id": scan_id,
        "policy_name": finding.policy_name,
        "resource_type": finding.resource_type.value,
        "resource_id": finding.resource_id,
        "resource_name": finding.resource_name,
        "compliant": finding.compliant,
        "effect": finding.effect.value,
        "enforcement": finding.enforcement.value,
        "message": finding.message,
        "remediation": finding.remediation,
        "owner": finding.owner,
        "object_tags": _object_tags(config),
        "created_at": created_at,
    }


def row_to_finding(row: dict[str, Any]) -> Finding:
    """Deserialise a ``findings`` row into a finding.

    Args:
        row: The row mapping read from storage.

    Returns:
        The reconstructed finding.
    """
    return Finding(
        policy_name=str(row["policy_name"]),
        resource_type=ResourceType(row["resource_type"]),
        resource_id=_as_str(row.get("resource_id")) or "",
        resource_name=_as_str(row.get("resource_name")) or "",
        compliant=_as_bool(row.get("compliant")),
        effect=Effect(row["effect"]),
        enforcement=EnforcementLevel(row["enforcement"]),
        message=_as_str(row.get("message")) or "",
        remediation=_as_str(row.get("remediation")) or "",
        owner=_as_str(row.get("owner")),
    )


def approval_event_to_row(event: ApprovalEvent) -> dict[str, Any]:
    """Serialise an approval event to an ``approval_events`` row.

    Args:
        event: The approval event to serialise.

    Returns:
        A row mapping ready for insertion.
    """
    return {
        "event_id": event.event_id,
        "policy_name": event.policy_name,
        "from_status": event.from_status.value,
        "to_status": event.to_status.value,
        "actor": event.actor,
        "note": event.note,
        "created_at": event.created_at,
    }


def remediation_to_row(item: RemediationItem, config: StorageConfig) -> dict[str, Any]:
    """Serialise a remediation item to a ``remediations`` row.

    Args:
        item: The remediation item to serialise.
        config: Storage config supplying object tags.

    Returns:
        A row mapping ready for insertion.
    """
    return {
        "remediation_id": item.remediation_id,
        "finding_id": "",
        "scan_id": item.scan_id,
        "policy_name": item.policy_name,
        "resource_type": item.resource_type.value,
        "resource_id": item.resource_id,
        "resource_name": item.resource_name,
        "enforcement": item.enforcement.value,
        "status": item.status.value,
        "assignee": item.assignee,
        "note": item.note,
        "object_tags": _object_tags(config),
        "opened_at": item.opened_at,
        "updated_at": item.updated_at,
    }


def row_to_remediation(row: dict[str, Any]) -> RemediationItem:
    """Deserialise a ``remediations`` row into a remediation item.

    Args:
        row: The row mapping read from storage.

    Returns:
        The reconstructed remediation item.
    """
    return RemediationItem(
        remediation_id=str(row["remediation_id"]),
        policy_name=str(row["policy_name"]),
        resource_type=ResourceType(row["resource_type"]),
        resource_id=_as_str(row.get("resource_id")) or "",
        resource_name=_as_str(row.get("resource_name")) or "",
        enforcement=EnforcementLevel(row["enforcement"]),
        status=RemediationStatus(row["status"]),
        scan_id=_as_str(row.get("scan_id")) or "",
        opened_at=_as_datetime(row["opened_at"]),
        updated_at=_as_datetime(row["updated_at"]),
        assignee=_as_str(row.get("assignee")),
        note=_as_str(row.get("note")) or "",
    )


def schedule_to_row(
    schedule: ScanSchedule, config: StorageConfig, updated_at: datetime
) -> dict[str, Any]:
    """Serialise a scan schedule to a ``schedules`` row.

    Args:
        schedule: The schedule to serialise.
        config: Storage config supplying object tags.
        updated_at: Timestamp recorded on the row.

    Returns:
        A row mapping ready for insertion.
    """
    return {
        "schedule_id": schedule.schedule_id,
        "name": schedule.name,
        "cron": schedule.cron,
        "timezone": schedule.timezone,
        "policy_names": json.dumps(list(schedule.policy_names)),
        "resource_types": json.dumps([rt.value for rt in schedule.resource_types]),
        "paused": schedule.paused,
        "object_tags": _object_tags(config),
        "updated_at": updated_at,
    }


def row_to_schedule(row: dict[str, Any]) -> ScanSchedule:
    """Deserialise a ``schedules`` row into a scan schedule.

    Args:
        row: The row mapping read from storage.

    Returns:
        The reconstructed schedule.
    """
    return ScanSchedule(
        schedule_id=str(row["schedule_id"]),
        name=_as_str(row.get("name")) or "",
        cron=_as_str(row.get("cron")) or "",
        timezone=_as_str(row.get("timezone")) or "UTC",
        policy_names=tuple(_loads(row.get("policy_names")) or ()),
        resource_types=tuple(
            ResourceType(value) for value in (_loads(row.get("resource_types")) or ())
        ),
        paused=_as_bool(row.get("paused")),
    )


def role_mapping_to_row(
    group_name: str, role: Role, config: StorageConfig, updated_at: datetime
) -> dict[str, Any]:
    """Serialise a group-to-role grant to a ``role_mappings`` row.

    Args:
        group_name: The workspace group being granted a role.
        role: The granted role.
        config: Storage config supplying object tags.
        updated_at: Timestamp recorded on the row.

    Returns:
        A row mapping ready for insertion.
    """
    return {
        "group_name": group_name,
        "role": role.value,
        "object_tags": _object_tags(config),
        "updated_at": updated_at,
    }


def _object_tags(config: StorageConfig) -> str:
    return json.dumps(dict(config.object_tags), sort_keys=True)


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _loads(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, dict | list):
        return value
    return json.loads(value)


def _as_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _as_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "t", "1", "yes"}
