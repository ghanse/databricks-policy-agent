"""Pure functions that drive the remediation cycle.

A violation is tracked by the ``(policy, resource type, resource id)`` it concerns.
``reconcile`` diffs the currently-open items against a fresh scan's violations: new
violations open items, and open items whose violation has cleared are auto-resolved. The
manual transitions (`advance`, `resolve`, `waive`, `assign`) let an
owner move an item by hand.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime

from policy_agent.remediation.model import RemediationItem, RemediationStatus
from policy_agent.scan.results import Finding

_ViolationKey = tuple[str, str, str]


def reconcile(
    existing_items: Iterable[RemediationItem],
    violations: Iterable[Finding],
    scan_id: str,
    now: datetime,
) -> list[RemediationItem]:
    """Reconciles open remediation items against a fresh scan's violations.

    Args:
        existing_items: Remediation items already tracked from earlier scans.
        violations: The violating findings from the latest scan.
        scan_id: Identifier of the latest scan.
        now: Timestamp applied to any status change.

    Returns:
        The updated set of remediation items: unchanged resolved/waived items, auto-resolved
        items whose violation has cleared, still-open items, and newly opened items.
    """
    violations_by_key = {_finding_key(finding): finding for finding in violations}
    existing_keys: set[_ViolationKey] = set()
    reconciled: list[RemediationItem] = []

    for item in existing_items:
        key = _item_key(item)
        existing_keys.add(key)
        if item.is_open and key not in violations_by_key:
            reconciled.append(
                replace(
                    item,
                    status=RemediationStatus.RESOLVED,
                    note="Auto-resolved: resource no longer violates the policy.",
                    updated_at=now,
                )
            )
        else:
            reconciled.append(item)

    for key, finding in violations_by_key.items():
        if key not in existing_keys:
            reconciled.append(_open_item(finding, scan_id, now))
    return reconciled


def open_items_from_findings(
    violations: Iterable[Finding], scan_id: str, now: datetime
) -> list[RemediationItem]:
    """Opens a fresh remediation item for every violation.

    Args:
        violations: The violating findings.
        scan_id: Identifier of the scan that produced them.
        now: Timestamp applied to the opened items.

    Returns:
        One open remediation item per violation.
    """
    return reconcile([], violations, scan_id, now)


def advance(item: RemediationItem, now: datetime, note: str = "") -> RemediationItem:
    """Marks an item as in progress.

    Args:
        item: The item to advance.
        now: Timestamp of the change.
        note: Optional note recorded on the item.

    Returns:
        The updated item.
    """
    return _set_status(item, RemediationStatus.IN_PROGRESS, now, note)


def resolve(item: RemediationItem, now: datetime, note: str = "") -> RemediationItem:
    """Marks an item as resolved.

    Args:
        item: The item to resolve.
        now: Timestamp of the change.
        note: Optional note recorded on the item.

    Returns:
        The updated item.
    """
    return _set_status(item, RemediationStatus.RESOLVED, now, note)


def waive(item: RemediationItem, now: datetime, note: str = "") -> RemediationItem:
    """Waives an item, accepting the violation without changing the resource.

    Args:
        item: The item to waive.
        now: Timestamp of the change.
        note: Optional justification recorded on the item.

    Returns:
        The updated item.
    """
    return _set_status(item, RemediationStatus.WAIVED, now, note)


def assign(item: RemediationItem, assignee: str, now: datetime) -> RemediationItem:
    """Assigns an item to a principal responsible for resolving it.

    Args:
        item: The item to assign.
        assignee: The principal to assign.
        now: Timestamp of the change.

    Returns:
        The updated item.
    """
    return replace(item, assignee=assignee, updated_at=now)


def _open_item(finding: Finding, scan_id: str, now: datetime) -> RemediationItem:
    return RemediationItem(
        remediation_id=uuid.uuid4().hex,
        policy_name=finding.policy_name,
        resource_type=finding.resource_type,
        resource_id=finding.resource_id,
        resource_name=finding.resource_name,
        enforcement_level=finding.enforcement_level,
        status=RemediationStatus.OPEN,
        scan_id=scan_id,
        opened_at=now,
        updated_at=now,
    )


def _set_status(
    item: RemediationItem, status: RemediationStatus, now: datetime, note: str
) -> RemediationItem:
    return replace(item, status=status, updated_at=now, note=note or item.note)


def _finding_key(finding: Finding) -> _ViolationKey:
    return (finding.policy_name, finding.resource_type.value, finding.resource_id)


def _item_key(item: RemediationItem) -> _ViolationKey:
    return (item.policy_name, item.resource_type.value, item.resource_id)
