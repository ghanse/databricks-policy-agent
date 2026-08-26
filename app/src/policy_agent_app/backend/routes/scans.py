"""Scans trigger and result endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.jobs.runner import run_policy_scan
from policy_agent.policy.model import PolicyStatus, ResourceType
from policy_agent.scan.engine import run_scan
from policy_agent.storage.backend import (
    SqlExecutor,
    load_policies,
    read_findings,
    read_scans,
)

from policy_agent_app.backend.auth import current_user, require_runner
from policy_agent_app.backend.dependencies import (
    get_config,
    get_executor,
    get_workspace_client,
)
from policy_agent_app.backend.schemas import ScanRequest, finding_to_dict, scan_result_to_dict

router = APIRouter(tags=["scans"])


@router.post("/scans")
def trigger_scan(
    body: ScanRequest,
    user: str = Depends(current_user),
    _roles: set[Role] = Depends(require_runner),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    workspace_client=Depends(get_workspace_client),
) -> dict[str, Any]:
    """Runs a scan of the approved policies (optionally a subset) and return its summary."""
    policies = load_policies(executor, config.storage, status=PolicyStatus.APPROVED)
    if body.policy_names:
        wanted = set(body.policy_names)
        policies = [policy for policy in policies if policy.name in wanted]
    resource_types = (
        [ResourceType(value) for value in body.resource_types] if body.resource_types else None
    )
    if body.dry_run:
        result = run_scan(workspace_client, policies, resource_types)
    else:
        result = run_policy_scan(
            workspace_client, executor, config, policies, f"app:{user}", resource_types
        )
    return scan_result_to_dict(result)


@router.get("/scans")
def list_scans(
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """Lists scan header rows, most recent first."""
    return read_scans(executor, config.storage)


@router.get("/scans/{scan_id}/findings")
def scan_findings(
    scan_id: str,
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """Returns the findings for a single scan."""
    return [
        finding_to_dict(finding) for finding in read_findings(executor, config.storage, scan_id)
    ]
