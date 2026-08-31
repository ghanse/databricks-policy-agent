"""Policy CRUD and validation endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.errors import PolicyAgentError
from policy_agent.policy import policy_from_dict, policy_to_dict, validate_policy
from policy_agent.policy.model import PolicyStatus
from policy_agent.policy.yaml_loader import dump_policies_to_yaml, load_policies_from_yaml
from policy_agent.storage.backend import (
    SqlExecutor,
    delete_policy,
    load_policies,
    read_approval_events,
    save_policy,
)

from policy_agent_app.backend.auth import current_user, require_admin, require_author
from policy_agent_app.backend.dependencies import get_config, get_effective_config, get_executor
from policy_agent_app.backend.lookups import find_policy
from policy_agent_app.backend.schemas import PolicyImportRequest, PolicyRequest

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("")
def list_policies(
    status_filter: str | None = Query(None, alias="status"),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """List policies, optionally filtered by approval status."""
    parsed = PolicyStatus(status_filter) if status_filter else None
    return [policy_to_dict(policy) for policy in load_policies(executor, config.storage, parsed)]


@router.post("/validate")
def validate_policy_request(body: PolicyRequest) -> dict[str, Any]:
    """Validate a policy definition without persisting it."""
    try:
        validate_policy(policy_from_dict(body.to_policy_dict()))
    except PolicyAgentError as error:
        return {"valid": False, "error": str(error)}
    return {"valid": True}


@router.post("/parse")
def parse_policies(
    body: PolicyImportRequest,
    _roles: set[Role] = Depends(require_author),
) -> dict[str, Any]:
    """Parse OPA-style YAML into policy dictionaries without saving them.

    Requires author permission (same as importing), so the parser is not reachable
    anonymously. Used by the UI to populate the authoring form from an uploaded file so the
    user can review and confirm before saving.
    """
    policies = load_policies_from_yaml(body.yaml)
    return {"policies": [policy_to_dict(policy) for policy in policies]}


@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_policies(
    body: PolicyImportRequest,
    user: str = Depends(current_user),
    _roles: set[Role] = Depends(require_author),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_effective_config),
) -> dict[str, Any]:
    """Import one or more policies from OPA-style YAML text, each saved as a draft."""
    policies = load_policies_from_yaml(body.yaml)
    for policy in policies:
        save_policy(executor, config.storage, policy, actor=user)
    return {"imported": [policy.name for policy in policies], "count": len(policies)}


@router.get("/{name}")
def get_policy(
    name: str,
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> dict[str, Any]:
    """Return a single policy by name."""
    return policy_to_dict(find_policy(executor, config, name))


@router.get("/{name}/yaml")
def get_policy_yaml(
    name: str,
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> dict[str, str]:
    """Return a single policy rendered as OPA-style YAML."""
    return {"yaml": dump_policies_to_yaml([find_policy(executor, config, name)])}


@router.get("/{name}/history")
def policy_history(
    name: str,
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """Return the approval-event history for a policy, most recent first."""
    return read_approval_events(executor, config.storage, policy_name=name)


@router.post("", status_code=status.HTTP_201_CREATED)
def upsert_policy(
    body: PolicyRequest,
    user: str = Depends(current_user),
    _roles: set[Role] = Depends(require_author),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_effective_config),
) -> dict[str, Any]:
    """Create or update a policy (saved in draft status by the author)."""
    policy = policy_from_dict(body.to_policy_dict())
    validate_policy(policy)
    save_policy(executor, config.storage, policy, actor=user)
    return policy_to_dict(policy)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_policy(
    name: str,
    _roles: set[Role] = Depends(require_admin),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> None:
    """Delete a policy by name."""
    delete_policy(executor, config.storage, name)
