"""Pydantic request bodies and response serializers for the JSON API."""

from __future__ import annotations

from typing import Any

from policy_agent.remediation.model import RemediationItem
from policy_agent.scan.results import Finding, ScanResult
from policy_agent.schedule import ScanSchedule
from pydantic import BaseModel


class PolicyRequest(BaseModel):
    """Request body for creating or updating a policy."""

    name: str
    resource_type: str
    effect: str
    rule: dict[str, Any]
    description: str = ""
    severity: str = "medium"
    match: dict[str, Any] | None = None
    remediation: str = ""

    def to_policy_dict(self) -> dict[str, Any]:
        """Convert the request to the canonical policy dictionary form.

        Returns:
            A mapping accepted by :func:`policy_agent.policy.policy_from_dict`.
        """
        data: dict[str, Any] = {
            "policy": self.name,
            "resource_type": self.resource_type,
            "effect": self.effect,
            "rule": self.rule,
            "description": self.description,
            "severity": self.severity,
            "remediation": self.remediation,
        }
        if self.match is not None:
            data["match"] = self.match
        return data


class NoteRequest(BaseModel):
    """Request body carrying an optional justification note for a transition."""

    note: str = ""


class ScanRequest(BaseModel):
    """Request body for triggering a scan."""

    resource_types: list[str] | None = None
    policy_names: list[str] | None = None
    dry_run: bool = False


class RemediationActionRequest(BaseModel):
    """Request body for advancing a remediation item."""

    action: str
    note: str = ""
    assignee: str | None = None


class RoleMappingRequest(BaseModel):
    """Request body for granting or revoking a group role."""

    group_name: str
    role: str


class PolicyImportRequest(BaseModel):
    """Request body carrying one or more policies as OPA-style YAML text."""

    yaml: str


class SettingsUpdateRequest(BaseModel):
    """Admin-editable configuration overrides. Fields left unset are not changed."""

    object_tags: dict[str, str] | None = None
    notification_emails: list[str] | None = None
    notification_webhook: str | None = None


class ScheduleRequest(BaseModel):
    """Request body for creating or updating a scan schedule."""

    name: str
    cron: str
    timezone: str = "UTC"
    policy_names: list[str] = []
    resource_types: list[str] = []
    paused: bool = False
    schedule_id: str | None = None


def remediation_to_dict(item: RemediationItem) -> dict[str, Any]:
    """Serialise a remediation item for a JSON response.

    Args:
        item: The remediation item.

    Returns:
        A JSON-serialisable mapping.
    """
    return {
        "remediation_id": item.remediation_id,
        "policy_name": item.policy_name,
        "resource_type": item.resource_type.value,
        "resource_id": item.resource_id,
        "resource_name": item.resource_name,
        "severity": item.severity.value,
        "status": item.status.value,
        "assignee": item.assignee,
        "note": item.note,
        "scan_id": item.scan_id,
        "opened_at": item.opened_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def finding_to_dict(finding: Finding) -> dict[str, Any]:
    """Serialise a finding for a JSON response.

    Args:
        finding: The finding.

    Returns:
        A JSON-serialisable mapping.
    """
    return {
        "policy_name": finding.policy_name,
        "resource_type": finding.resource_type.value,
        "resource_id": finding.resource_id,
        "resource_name": finding.resource_name,
        "compliant": finding.compliant,
        "severity": finding.severity.value,
        "message": finding.message,
        "remediation": finding.remediation,
        "owner": finding.owner,
    }


def scan_result_to_dict(result: ScanResult) -> dict[str, Any]:
    """Serialise a scan result and its summary for a JSON response.

    Args:
        result: The scan result.

    Returns:
        A JSON-serialisable mapping with the scan id, summary, and violations.
    """
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
            "violations_by_severity": dict(summary.violations_by_severity),
            "violations_by_resource_type": dict(summary.violations_by_resource_type),
        },
        "violations": [finding_to_dict(finding) for finding in result.violations],
    }


def schedule_to_dict(schedule: ScanSchedule) -> dict[str, Any]:
    """Serialise a scan schedule for a JSON response.

    Args:
        schedule: The scan schedule.

    Returns:
        A JSON-serialisable mapping.
    """
    return {
        "schedule_id": schedule.schedule_id,
        "name": schedule.name,
        "cron": schedule.cron,
        "timezone": schedule.timezone,
        "policy_names": list(schedule.policy_names),
        "resource_types": [rt.value for rt in schedule.resource_types],
        "paused": schedule.paused,
    }
