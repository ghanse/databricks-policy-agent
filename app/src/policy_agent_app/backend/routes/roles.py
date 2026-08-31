"""Role membership and role-mapping endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.storage.backend import (
    SqlExecutor,
    delete_role_mapping,
    read_role_mappings,
    save_role_mapping,
)

from policy_agent_app.backend.auth import current_roles, current_user, require_admin
from policy_agent_app.backend.dependencies import get_config, get_executor, get_workspace_client
from policy_agent_app.backend.schemas import RoleMappingRequest

router = APIRouter(prefix="/roles", tags=["roles"])


def _display_name(workspace_client: Any, user: str) -> str:
    # Best-effort SCIM lookup of the caller's display name; falls back to empty.
    # Escape double quotes so a username can't break out of the quoted filter literal.
    escaped = user.replace("\\", "\\\\").replace('"', '\\"')
    try:
        for scim_user in workspace_client.users.list(filter=f'userName eq "{escaped}"'):
            name = getattr(scim_user, "display_name", None)
            if name:
                return str(name)
    except Exception:
        return ""
    return ""


@router.get("/me")
def my_roles(
    user: str = Depends(current_user),
    roles: set[Role] = Depends(current_roles),
    workspace_client=Depends(get_workspace_client),
) -> dict[str, Any]:
    """Return the caller's identity, display name, and effective roles."""
    return {
        "user": user,
        "display_name": _display_name(workspace_client, user),
        "roles": sorted(role.value for role in roles),
    }


@router.get("/mappings")
def list_role_mappings(
    _roles: set[Role] = Depends(require_admin),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> dict[str, list[str]]:
    """Return every group-to-role grant."""
    mappings = read_role_mappings(executor, config.storage)
    return {group: sorted(role.value for role in roles) for group, roles in mappings.items()}


@router.post("/mappings", status_code=status.HTTP_201_CREATED)
def grant_role(
    body: RoleMappingRequest,
    _roles: set[Role] = Depends(require_admin),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> dict[str, str]:
    """Grant a role to a workspace group."""
    save_role_mapping(executor, config.storage, body.group_name, Role(body.role))
    return {"group_name": body.group_name, "role": body.role}


@router.delete("/mappings", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def revoke_role(
    body: RoleMappingRequest,
    _roles: set[Role] = Depends(require_admin),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> None:
    """Revoke a role from a workspace group."""
    delete_role_mapping(executor, config.storage, body.group_name, Role(body.role))
