"""Approval-workflow transition endpoints (submit, approve, reject, archive)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends
from policy_agent.approval.roles import Role
from policy_agent.approval.workflow import (
    ApprovalEvent,
    approve,
    archive,
    reject,
    submit_for_review,
)
from policy_agent.config import PolicyAgentConfig
from policy_agent.policy import policy_to_dict
from policy_agent.policy.model import Policy
from policy_agent.storage.backend import SqlExecutor, save_approval_event, save_policy

from policy_agent_app.backend.auth import (
    current_user,
    require_admin,
    require_approver,
    require_author,
)
from policy_agent_app.backend.dependencies import get_config, get_executor
from policy_agent_app.backend.lookups import find_policy
from policy_agent_app.backend.schemas import NoteRequest

router = APIRouter(prefix="/policies", tags=["approvals"])

_Transition = Callable[[Policy, str, set[Role], str], tuple[Policy, ApprovalEvent]]


@router.post("/{name}/submit")
def submit(
    name: str,
    body: NoteRequest,
    user: str = Depends(current_user),
    roles: set[Role] = Depends(require_author),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> dict[str, Any]:
    """Submit a draft or rejected policy for review."""
    return _apply(submit_for_review, name, user, roles, body.note, executor, config)


@router.post("/{name}/approve")
def approve_policy(
    name: str,
    body: NoteRequest,
    user: str = Depends(current_user),
    roles: set[Role] = Depends(require_approver),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> dict[str, Any]:
    """Approve a policy under review."""
    return _apply(approve, name, user, roles, body.note, executor, config)


@router.post("/{name}/reject")
def reject_policy(
    name: str,
    body: NoteRequest,
    user: str = Depends(current_user),
    roles: set[Role] = Depends(require_approver),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> dict[str, Any]:
    """Reject a policy under review."""
    return _apply(reject, name, user, roles, body.note, executor, config)


@router.post("/{name}/archive")
def archive_policy(
    name: str,
    body: NoteRequest,
    user: str = Depends(current_user),
    roles: set[Role] = Depends(require_admin),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> dict[str, Any]:
    """Archive a policy, retiring it from scans."""
    return _apply(archive, name, user, roles, body.note, executor, config)


def _apply(
    transition: _Transition,
    name: str,
    user: str,
    roles: set[Role],
    note: str,
    executor: SqlExecutor,
    config: PolicyAgentConfig,
) -> dict[str, Any]:
    policy = find_policy(executor, config, name)
    updated, event = transition(policy, user, roles, note)
    save_policy(executor, config.storage, updated, actor=user)
    save_approval_event(executor, config.storage, event)
    return policy_to_dict(updated)
