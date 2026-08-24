from datetime import UTC, datetime

from policy_agent.policy.model import Effect, EnforcementLevel, ResourceType
from policy_agent.remediation import (
    RemediationStatus,
    advance,
    open_items_from_findings,
    reconcile,
    resolve,
    waive,
)
from policy_agent.scan.results import Finding

NOW = datetime(2026, 1, 1, tzinfo=UTC)
LATER = datetime(2026, 1, 2, tzinfo=UTC)


def _violation(resource_id, policy_name="sp-owned"):
    return Finding(
        policy_name=policy_name,
        resource_type=ResourceType.CLUSTER,
        resource_id=resource_id,
        resource_name=resource_id,
        compliant=False,
        effect=Effect.DENY,
        enforcement_level=EnforcementLevel.HARD,
        message="violation",
        remediation="fix it",
    )


def test_open_items_created_per_violation():
    items = open_items_from_findings([_violation("c1"), _violation("c2")], "scan-1", NOW)
    assert len(items) == 2
    assert all(item.status is RemediationStatus.OPEN for item in items)
    assert all(item.is_open for item in items)


def test_reconcile_auto_resolves_cleared_violations():
    opened = open_items_from_findings([_violation("c1"), _violation("c2")], "scan-1", NOW)
    reconciled = reconcile(opened, [_violation("c1")], "scan-2", LATER)

    by_resource = {item.resource_id: item for item in reconciled}
    assert by_resource["c1"].status is RemediationStatus.OPEN
    assert by_resource["c2"].status is RemediationStatus.RESOLVED
    assert "Auto-resolved" in by_resource["c2"].note


def test_reconcile_opens_new_and_preserves_terminal_items():
    opened = open_items_from_findings([_violation("c1")], "scan-1", NOW)
    waived = [waive(opened[0], NOW, note="accepted risk")]

    reconciled = reconcile(waived, [_violation("c1"), _violation("c2")], "scan-2", LATER)

    by_resource = {item.resource_id: item for item in reconciled}
    assert by_resource["c1"].status is RemediationStatus.WAIVED
    assert by_resource["c2"].status is RemediationStatus.OPEN


def test_manual_transitions_update_status_and_timestamp():
    (item,) = open_items_from_findings([_violation("c1")], "scan-1", NOW)
    in_progress = advance(item, LATER, note="investigating")
    assert in_progress.status is RemediationStatus.IN_PROGRESS
    assert in_progress.updated_at == LATER
    assert in_progress.note == "investigating"

    resolved = resolve(in_progress, LATER)
    assert resolved.status is RemediationStatus.RESOLVED
    assert resolved.is_open is False
    assert resolved.note == "investigating"
