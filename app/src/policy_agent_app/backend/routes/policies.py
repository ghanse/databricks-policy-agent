"""Policy CRUD and validation endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.errors import PolicyAgentError
from policy_agent.policy import policy_from_dict, policy_to_dict, validate_policy
from policy_agent.policy.model import PolicyStatus
from policy_agent.storage.backend import (
    SqlExecutor,
    delete_policy,
    load_policies,
    read_approval_events,
    save_policy,
)

from policy_agent_app.backend.auth import current_user, require_admin, require_author
from policy_agent_app.backend.dependencies import get_config, get_executor
from policy_agent_app.backend.lookups import find_policy
from policy_agent_app.backend.schemas import PolicyRequest

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("")
def list_policies(
    status_filter: str | None = Query(None, alias="status"),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """Lists policies, optionally filtered by approval status."""
    parsed = PolicyStatus(status_filter) if status_filter else None
    return [policy_to_dict(policy) for policy in load_policies(executor, config.storage, parsed)]


@router.post("/validate")
def validate_policy_request(body: PolicyRequest) -> dict[str, Any]:
    """Validates a policy definition without persisting it."""
    try:
        validate_policy(policy_from_dict(body.to_policy_dict()))
    except PolicyAgentError as error:
        return {"valid": False, "error": str(error)}
    return {"valid": True}


@router.get("/{name}")
def get_policy(
    name: str,
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> dict[str, Any]:
    """Returns a single policy by name."""
    return policy_to_dict(find_policy(executor, config, name))


@router.get("/{name}/history")
def policy_history(
    name: str,
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """Returns the approval-event history for a policy, most recent first."""
    return read_approval_events(executor, config.storage, policy_name=name)


@router.post("", status_code=status.HTTP_201_CREATED)
def upsert_policy(
    body: PolicyRequest,
    user: str = Depends(current_user),
    _roles: set[Role] = Depends(require_author),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> dict[str, Any]:
    """Creates or update a policy (saved in draft status by the author)."""
    policy = policy_from_dict(body.to_policy_dict())
    validate_policy(policy)
    save_policy(executor, config.storage, policy, actor=user)
    return policy_to_dict(policy)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def remove_policy(
    name: str,
    _roles: set[Role] = Depends(require_admin),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> None:
    """Deletes a policy by name."""
    delete_policy(executor, config.storage, name)
