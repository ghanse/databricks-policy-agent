"""Configurable persistence for policies, scans, findings, and workflow state.

Two interchangeable backends implement the same `SqlExecutor` surface: Unity Catalog
Delta (`DeltaSqlExecutor`) and Lakebase Postgres (imported separately to keep the
core install free of the optional SQLAlchemy dependency)::

    from policy_agent.storage import StorageConfig, DeltaSqlExecutor, ensure_storage
    from policy_agent.storage.lakebase import LakebaseSqlExecutor  # needs the 'lakebase' extra
"""

from policy_agent.storage.backend import (
    SqlExecutor,
    delete_policy,
    delete_role_mapping,
    delete_schedule,
    ensure_storage,
    load_policies,
    read_approval_events,
    read_findings,
    read_remediation_events,
    read_remediations,
    read_role_mappings,
    read_scans,
    read_schedules,
    save_approval_event,
    save_policy,
    save_remediation,
    save_remediation_event,
    save_role_mapping,
    save_schedule,
    write_scan,
)
from policy_agent.storage.config import (
    BACKEND_LAKEBASE,
    BACKEND_UNITY_CATALOG,
    StorageConfig,
)
from policy_agent.storage.delta import DeltaSqlExecutor

__all__ = [
    "BACKEND_LAKEBASE",
    "BACKEND_UNITY_CATALOG",
    "DeltaSqlExecutor",
    "SqlExecutor",
    "StorageConfig",
    "delete_policy",
    "delete_role_mapping",
    "delete_schedule",
    "ensure_storage",
    "load_policies",
    "read_approval_events",
    "read_findings",
    "read_remediation_events",
    "read_remediations",
    "read_role_mappings",
    "read_scans",
    "read_schedules",
    "save_approval_event",
    "save_policy",
    "save_remediation",
    "save_remediation_event",
    "save_role_mapping",
    "save_schedule",
    "write_scan",
]
