"""Remediation cycle endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.remediation.cycle import advance, assign, resolve, waive
from policy_agent.remediation.model import RemediationItem
from policy_agent.storage.backend import SqlExecutor, read_remediations, save_remediation

from policy_agent_app.backend.auth import current_user, require_runner
from policy_agent_app.backend.dependencies import get_config, get_executor
from policy_agent_app.backend.lookups import find_remediation
from policy_agent_app.backend.schemas import RemediationActionRequest, remediation_to_dict

router = APIRouter(prefix="/remediations", tags=["remediations"])


@router.get("")
def list_remediations(
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """Lists remediation items, most recently opened first."""
    return [remediation_to_dict(item) for item in read_remediations(executor, config.storage)]


@router.post("/{remediation_id}/action")
def act_on_remediation(
    remediation_id: str,
    body: RemediationActionRequest,
    _roles: set[Role] = Depends(require_runner),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> dict[str, Any]:
    """Advance, resolve, waive, or assign a remediation item."""
    item = find_remediation(executor, config, remediation_id)
    updated = _apply_action(item, body)
    save_remediation(executor, config.storage, updated)
    return remediation_to_dict(updated)


def _apply_action(item: RemediationItem, body: RemediationActionRequest) -> RemediationItem:
    now = datetime.now(UTC)
    if body.action == "advance":
        return advance(item, now, body.note)
    if body.action == "resolve":
        return resolve(item, now, body.note)
    if body.action == "waive":
        return waive(item, now, body.note)
    if body.action == "assign":
        if not body.assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The 'assign' action requires an 'assignee'.",
            )
        return assign(item, body.assignee, now)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown remediation action {body.action!r}.",
    )
