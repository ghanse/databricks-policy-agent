"""Shared scan-and-persist logic for the provisioned jobs.

``run_policy_scan`` is the single place that runs a scan, writes results, reconciles the
remediation cycle, and notifies — so the ad-hoc scan job and the scheduled scan job behave
identically apart from how they are triggered.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from policy_agent.config import PolicyAgentConfig, config_from_env, create_executor
from policy_agent.notify import notify_scan_result
from policy_agent.policy.model import Policy, PolicyStatus, ResourceType
from policy_agent.remediation.cycle import make_event, reconcile
from policy_agent.remediation.model import RemediationEventType, RemediationStatus
from policy_agent.scan.engine import run_scan
from policy_agent.scan.results import ScanResult
from policy_agent.storage.backend import (
    SqlExecutor,
    ensure_storage,
    load_policies,
    read_remediations,
    save_remediation,
    save_remediation_event,
    write_scan,
)

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient


def run_policy_scan(
    workspace_client: WorkspaceClient,
    executor: SqlExecutor,
    config: PolicyAgentConfig,
    policies: Iterable[Policy],
    triggered_by: str,
    resource_types: Iterable[ResourceType] | None = None,
    dry_run: bool = False,
) -> ScanResult:
    """Runs a scan and, unless ``dry_run``, persists results and reconciles remediations.

    Args:
        workspace_client: An authenticated Databricks workspace client.
        executor: The storage executor.
        config: The runtime configuration.
        policies: The policies to evaluate.
        triggered_by: Label recorded as the scan's initiator.
        resource_types: Optional restriction on scanned resource types.
        dry_run: When ``True`` the scan runs but nothing is written or notified.

    Returns:
        The completed `ScanResult`.
    """
    result = run_scan(workspace_client, policies, resource_types)
    if dry_run:
        return result
    ensure_storage(executor, config.storage)
    write_scan(executor, config.storage, result, triggered_by)
    _reconcile_remediations(executor, config, result, triggered_by)
    notify_scan_result(result, config.notification_webhook, config.notification_emails)
    return result


def execute_scan_job(triggered_by: str) -> int:
    """Runs a full scan of every approved policy from the environment configuration.

    Builds the workspace client and storage executor from the ambient environment (as set by
    the Databricks Asset Bundle), scans all approved policies, and persists the outcome.

    Args:
        triggered_by: Label recorded as the scan's initiator.

    Returns:
        Process exit code: ``0`` on success, ``1`` on error.
    """
    from databricks.sdk import WorkspaceClient

    config = config_from_env()
    workspace_client = WorkspaceClient()
    executor = create_executor(config, workspace_client)
    policies = load_policies(executor, config.storage, status=PolicyStatus.APPROVED)
    result = run_policy_scan(workspace_client, executor, config, policies, triggered_by)
    summary = result.summary()
    print(
        f"scan {result.scan_id}: evaluated {summary.evaluated}, "
        f"violations {summary.violations}, compliance {summary.compliance_rate:.1%}"
    )
    return 0


def _reconcile_remediations(
    executor: SqlExecutor, config: PolicyAgentConfig, result: ScanResult, triggered_by: str
) -> None:
    now = datetime.now(UTC)
    existing = read_remediations(executor, config.storage)
    existing_by_id = {item.remediation_id: item for item in existing}
    updated = reconcile(existing, result.violations, result.scan_id, now)
    for item in updated:
        save_remediation(executor, config.storage, item)
        event = _reconcile_event(item, existing_by_id.get(item.remediation_id), triggered_by, now)
        if event is not None:
            save_remediation_event(executor, config.storage, event)


def _reconcile_event(item, previous, actor, now):
    """Builds the audit event for a reconciled item, or ``None`` when nothing changed."""
    if previous is None:
        return make_event(
            item.remediation_id,
            RemediationEventType.OPENED,
            actor,
            now,
            note="Opened for a new violation.",
            to_status=item.status,
        )
    if previous.status != item.status and item.status is RemediationStatus.RESOLVED:
        return make_event(
            item.remediation_id,
            RemediationEventType.AUTO_RESOLVED,
            actor,
            now,
            note=item.note,
            from_status=previous.status,
            to_status=item.status,
        )
    return None
