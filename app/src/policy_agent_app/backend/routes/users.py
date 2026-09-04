"""Account-user lookup that backs the assignee typeahead.

Remediation assignment is limited to real principals in the account rather than free-text
email. A Databricks App runs with on-behalf-of scopes that reach the account's users through
the workspace SCIM ``Users`` API (the same surface :mod:`auth` uses for group lookup), so
that is what the typeahead queries; the results are the account users provisioned to this
workspace.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from policy_agent_app.backend.auth import current_user
from policy_agent_app.backend.dependencies import get_workspace_client

router = APIRouter(prefix="/users", tags=["users"])

_MAX_RESULTS = 20


@router.get("/search")
def search_users(
    q: str = Query("", description="Prefix or substring to match on name or email."),
    limit: int = Query(10, ge=1, le=_MAX_RESULTS),
    workspace_client=Depends(get_workspace_client),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """Return active account users whose email or display name matches ``q``."""
    return find_users(workspace_client, q, limit)


def find_users(workspace_client: Any, query: str, limit: int) -> list[dict[str, Any]]:
    """Looks up active users matching a query, for the assignee typeahead.

    Args:
        workspace_client: The workspace client used for the SCIM lookup.
        query: Prefix or substring matched against user name and display name.
        limit: Maximum number of users to return.

    Returns:
        Matching users as ``{"user_name", "display_name", "active"}`` mappings. Lookup is
        best-effort: a permissions error or unsupported API yields an empty list rather than
        failing the request.
    """
    scim_filter = _scim_filter(query)
    try:
        matches = workspace_client.users.list(
            filter=scim_filter, count=limit, attributes="userName,displayName,active"
        )
    except Exception:
        return []
    users: list[dict[str, Any]] = []
    for scim_user in matches:
        user_name = getattr(scim_user, "user_name", None)
        if not user_name or getattr(scim_user, "active", True) is False:
            continue
        users.append(
            {
                "user_name": user_name,
                "display_name": getattr(scim_user, "display_name", None) or user_name,
                "active": True,
            }
        )
        if len(users) >= limit:
            break
    return users


def _scim_filter(query: str) -> str | None:
    # SCIM's ``co`` (contains) operator lets one query match either the email or the name.
    cleaned = query.strip().replace('"', "")
    if not cleaned:
        return None
    return f'userName co "{cleaned}" or displayName co "{cleaned}"'
