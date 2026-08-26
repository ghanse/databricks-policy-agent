"""Read-only metadata about the deployment's configuration and vocabulary."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.policy.conditions import registered_operators
from policy_agent.scan.registry import supported_resource_types

from policy_agent_app.backend.auth import current_user
from policy_agent_app.backend.dependencies import get_config

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings(
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> dict[str, Any]:
    """Returns non-sensitive deployment metadata and the policy vocabulary."""
    storage = config.storage
    return {
        "storage": {
            "backend": storage.backend,
            "catalog": storage.catalog,
            "schema": storage.schema,
            "qualified_schema": storage.qualified_schema,
            "object_tags": dict(storage.object_tags),
        },
        "resource_types": [rt.value for rt in supported_resource_types()],
        "operators": list(registered_operators()),
        "roles": [role.value for role in Role],
        "notifications": {
            "emails": list(config.notification_emails),
            "webhook_configured": bool(config.notification_webhook),
        },
    }
