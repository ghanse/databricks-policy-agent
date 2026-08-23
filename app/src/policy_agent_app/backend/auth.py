"""Caller identity and role-based authorization.

A Databricks App forwards the signed-in user's email in the ``X-Forwarded-Email`` header.
The caller's roles are the union of roles mapped to their workspace groups. As a bootstrap
convenience, when no role mappings exist yet every caller is treated as an administrator so
the first admin can be configured through the app itself.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status
from policy_agent.approval.roles import (
    Role,
    can_administer,
    can_approve,
    can_author,
    can_run_scans,
    resolve_roles,
)
from policy_agent.config import PolicyAgentConfig
from policy_agent.storage.backend import SqlExecutor, read_role_mappings

from policy_agent_app.backend.dependencies import (
    get_config,
    get_executor,
    get_workspace_client,
)

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

_LOCAL_DEV_USER = "local-dev@databricks.com"


def current_user(request: Request) -> str:
    """Return the signed-in user's email from the forwarded identity header.

    Args:
        request: The incoming request.

    Returns:
        The caller's email, or a local-development placeholder when unset.
    """
    return request.headers.get("X-Forwarded-Email", _LOCAL_DEV_USER)


def current_roles(
    user: str = Depends(current_user),
    workspace_client: WorkspaceClient = Depends(get_workspace_client),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
) -> set[Role]:
    """Resolve the caller's effective roles from their group memberships.

    Args:
        user: The caller's email.
        workspace_client: The workspace client used to look up group membership.
        executor: The storage executor.
        config: The runtime configuration.

    Returns:
        The caller's effective roles.
    """
    role_mappings = read_role_mappings(executor, config.storage)
    if not role_mappings:
        return {Role.ADMIN}
    return resolve_roles(_user_groups(workspace_client, user), role_mappings)


def resolve_caller_roles(groups: Collection[str], role_mappings: dict[str, set[Role]]) -> set[Role]:
    """Resolve roles for a caller, granting admin when no mappings are configured.

    Args:
        groups: The caller's workspace groups.
        role_mappings: The configured group-to-role grants.

    Returns:
        The caller's effective roles.
    """
    if not role_mappings:
        return {Role.ADMIN}
    return resolve_roles(groups, role_mappings)


def require(
    predicate: Callable[[Collection[Role]], bool], action: str
) -> Callable[[set[Role]], set[Role]]:
    """Build a dependency that authorizes a request against a permission predicate.

    Args:
        predicate: Returns whether a set of roles permits the action.
        action: Human-readable action name used in the error message.

    Returns:
        A FastAPI dependency that returns the caller's roles or raises ``403``.
    """

    def dependency(roles: set[Role] = Depends(current_roles)) -> set[Role]:
        if not predicate(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Caller is not permitted to {action}.",
            )
        return roles

    return dependency


require_author = require(can_author, "author policies")
require_approver = require(can_approve, "approve or reject policies")
require_runner = require(can_run_scans, "run scans")
require_admin = require(can_administer, "perform administrative actions")


def _user_groups(workspace_client: WorkspaceClient, user: str) -> list[str]:
    # Group lookup is best-effort: an unknown user or a permissions error yields no roles
    # rather than failing the request.
    try:
        matches = list(workspace_client.users.list(filter=f'userName eq "{user}"'))
    except Exception:
        return []
    groups: list[str] = []
    for scim_user in matches:
        for group in getattr(scim_user, "groups", None) or []:
            display = getattr(group, "display", None)
            if display:
                groups.append(display)
    return groups
