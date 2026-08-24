"""High-level persistence functions over a backend-agnostic SQL executor.

These functions are the storage API the rest of the framework calls. Each takes a
`SqlExecutor` and a `StorageConfig`, builds SQL with `schema`, and maps
rows with `records`. Mutable entities are upserted with delete-then-insert so no
vendor-specific ``MERGE``/``ON CONFLICT`` is required.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from policy_agent.approval.roles import Role
from policy_agent.approval.workflow import ApprovalEvent
from policy_agent.policy.model import Policy, PolicyStatus
from policy_agent.remediation.model import RemediationItem
from policy_agent.scan.results import Finding, ScanResult
from policy_agent.schedule import ScanSchedule
from policy_agent.storage import records, schema
from policy_agent.storage.config import StorageConfig


class SqlExecutor(Protocol):
    """The minimal SQL surface both storage backends implement."""

    def execute(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        """Execute a statement that returns no rows.

        Args:
            statement: SQL text with ``:name`` parameter markers.
            parameters: Named parameter values, if any.
        """
        ...

    def query(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a query and return its rows as column-keyed mappings.

        Args:
            statement: SQL text with ``:name`` parameter markers.
            parameters: Named parameter values, if any.

        Returns:
            The result rows.
        """
        ...


def ensure_storage(executor: SqlExecutor, config: StorageConfig) -> None:
    """Create the namespace and every table if they do not already exist.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
    """
    for statement in schema.create_namespace_statements(config):
        executor.execute(statement)
    for statement in schema.create_table_statements(config):
        executor.execute(statement)


def save_policy(
    executor: SqlExecutor, config: StorageConfig, policy: Policy, actor: str = "system"
) -> None:
    """Upsert a policy and append a version snapshot.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        policy: The policy to persist.
        actor: The principal recorded as author of this version.
    """
    now = datetime.now(UTC)
    delete_sql, delete_params = schema.delete_statement(config, "policies", {"name": policy.name})
    executor.execute(delete_sql, delete_params)
    insert_sql, insert_params = schema.insert_statement(
        config, "policies", records.policy_to_row(policy, config, now)
    )
    executor.execute(insert_sql, insert_params)
    version_sql, version_params = schema.insert_statement(
        config, "policy_versions", records.policy_version_to_row(policy, actor, now)
    )
    executor.execute(version_sql, version_params)


def load_policies(
    executor: SqlExecutor, config: StorageConfig, status: PolicyStatus | None = None
) -> list[Policy]:
    """Load policies, optionally filtered by approval status.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        status: When provided, only policies in this status are returned.

    Returns:
        The matching policies.
    """
    where = {"status": status.value} if status is not None else None
    sql, params = schema.select_statement(config, "policies", where=where, order_by="name")
    return [records.row_to_policy(row) for row in executor.query(sql, params)]


def delete_policy(executor: SqlExecutor, config: StorageConfig, name: str) -> None:
    """Delete a policy by name.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        name: The policy name to delete.
    """
    sql, params = schema.delete_statement(config, "policies", {"name": name})
    executor.execute(sql, params)


def write_scan(
    executor: SqlExecutor,
    config: StorageConfig,
    scan_result: ScanResult,
    triggered_by: str = "system",
) -> None:
    """Persist a scan's header row and one row per finding.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        scan_result: The completed scan result.
        triggered_by: Principal or process that initiated the scan.
    """
    scan_sql, scan_params = schema.insert_statement(
        config, "scans", records.scan_to_row(scan_result, config, triggered_by)
    )
    executor.execute(scan_sql, scan_params)
    for finding in scan_result.findings:
        row = records.finding_to_row(finding, scan_result.scan_id, config, scan_result.finished_at)
        finding_sql, finding_params = schema.insert_statement(config, "findings", row)
        executor.execute(finding_sql, finding_params)


def read_findings(
    executor: SqlExecutor, config: StorageConfig, scan_id: str | None = None
) -> list[Finding]:
    """Read findings, optionally restricted to a single scan.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        scan_id: When provided, only findings from this scan are returned.

    Returns:
        The matching findings.
    """
    where = {"scan_id": scan_id} if scan_id is not None else None
    sql, params = schema.select_statement(config, "findings", where=where)
    return [records.row_to_finding(row) for row in executor.query(sql, params)]


def read_scans(executor: SqlExecutor, config: StorageConfig) -> list[dict[str, Any]]:
    """Read scan header rows, most recent first.

    Args:
        executor: The SQL executor.
        config: The storage configuration.

    Returns:
        The scan header rows as column-keyed mappings.
    """
    sql, params = schema.select_statement(config, "scans", order_by="started_at DESC")
    return executor.query(sql, params)


def save_approval_event(executor: SqlExecutor, config: StorageConfig, event: ApprovalEvent) -> None:
    """Append an approval-workflow audit event.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        event: The approval event to persist.
    """
    sql, params = schema.insert_statement(
        config, "approval_events", records.approval_event_to_row(event)
    )
    executor.execute(sql, params)


def read_approval_events(
    executor: SqlExecutor, config: StorageConfig, policy_name: str | None = None
) -> list[dict[str, Any]]:
    """Read approval events, optionally for a single policy, most recent first.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        policy_name: When provided, only events for this policy are returned.

    Returns:
        The approval-event rows as column-keyed mappings.
    """
    where = {"policy_name": policy_name} if policy_name is not None else None
    sql, params = schema.select_statement(
        config, "approval_events", where=where, order_by="created_at DESC"
    )
    return executor.query(sql, params)


def save_remediation(executor: SqlExecutor, config: StorageConfig, item: RemediationItem) -> None:
    """Upsert a remediation item.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        item: The remediation item to persist.
    """
    delete_sql, delete_params = schema.delete_statement(
        config, "remediations", {"remediation_id": item.remediation_id}
    )
    executor.execute(delete_sql, delete_params)
    insert_sql, insert_params = schema.insert_statement(
        config, "remediations", records.remediation_to_row(item, config)
    )
    executor.execute(insert_sql, insert_params)


def read_remediations(executor: SqlExecutor, config: StorageConfig) -> list[RemediationItem]:
    """Read every remediation item.

    Args:
        executor: The SQL executor.
        config: The storage configuration.

    Returns:
        The remediation items.
    """
    sql, params = schema.select_statement(config, "remediations", order_by="opened_at DESC")
    return [records.row_to_remediation(row) for row in executor.query(sql, params)]


def save_schedule(executor: SqlExecutor, config: StorageConfig, schedule: ScanSchedule) -> None:
    """Upsert a scan schedule.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        schedule: The schedule to persist.
    """
    now = datetime.now(UTC)
    delete_sql, delete_params = schema.delete_statement(
        config, "schedules", {"schedule_id": schedule.schedule_id}
    )
    executor.execute(delete_sql, delete_params)
    insert_sql, insert_params = schema.insert_statement(
        config, "schedules", records.schedule_to_row(schedule, config, now)
    )
    executor.execute(insert_sql, insert_params)


def read_schedules(executor: SqlExecutor, config: StorageConfig) -> list[ScanSchedule]:
    """Read every scan schedule.

    Args:
        executor: The SQL executor.
        config: The storage configuration.

    Returns:
        The scan schedules.
    """
    sql, params = schema.select_statement(config, "schedules", order_by="name")
    return [records.row_to_schedule(row) for row in executor.query(sql, params)]


def delete_schedule(executor: SqlExecutor, config: StorageConfig, schedule_id: str) -> None:
    """Delete a scan schedule by id.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        schedule_id: The schedule to delete.
    """
    sql, params = schema.delete_statement(config, "schedules", {"schedule_id": schedule_id})
    executor.execute(sql, params)


def save_role_mapping(
    executor: SqlExecutor, config: StorageConfig, group_name: str, role: Role
) -> None:
    """Grant a role to a workspace group (idempotent).

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        group_name: The workspace group to grant the role to.
        role: The role being granted.
    """
    key = {"group_name": group_name, "role": role.value}
    delete_sql, delete_params = schema.delete_statement(config, "role_mappings", key)
    executor.execute(delete_sql, delete_params)
    insert_sql, insert_params = schema.insert_statement(
        config,
        "role_mappings",
        records.role_mapping_to_row(group_name, role, config, datetime.now(UTC)),
    )
    executor.execute(insert_sql, insert_params)


def delete_role_mapping(
    executor: SqlExecutor, config: StorageConfig, group_name: str, role: Role
) -> None:
    """Revoke a role from a workspace group.

    Args:
        executor: The SQL executor.
        config: The storage configuration.
        group_name: The workspace group to revoke the role from.
        role: The role being revoked.
    """
    sql, params = schema.delete_statement(
        config, "role_mappings", {"group_name": group_name, "role": role.value}
    )
    executor.execute(sql, params)


def read_role_mappings(executor: SqlExecutor, config: StorageConfig) -> dict[str, set[Role]]:
    """Read all group-to-role grants.

    Args:
        executor: The SQL executor.
        config: The storage configuration.

    Returns:
        A mapping from group name to the set of roles granted to it.
    """
    sql, params = schema.select_statement(config, "role_mappings")
    mappings: dict[str, set[Role]] = {}
    for row in executor.query(sql, params):
        mappings.setdefault(str(row["group_name"]), set()).add(Role(row["role"]))
    return mappings
