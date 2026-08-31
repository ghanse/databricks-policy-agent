"""Deployment configuration: effective settings and admin-editable overrides."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.policy.conditions import registered_operators
from policy_agent.scan.registry import supported_resource_types
from policy_agent.storage.backend import (
    SqlExecutor,
    ensure_storage,
    read_app_settings,
    save_app_setting,
)

from policy_agent_app.backend.auth import current_user, require_admin
from policy_agent_app.backend.dependencies import (
    SETTING_NOTIFICATION_EMAILS,
    SETTING_NOTIFICATION_WEBHOOK,
    SETTING_OBJECT_TAGS,
    apply_overrides,
    get_config,
    get_effective_config,
    get_executor,
    get_workspace_client,
)
from policy_agent_app.backend.schemas import SettingsUpdateRequest

router = APIRouter(prefix="/settings", tags=["settings"])


def _payload(
    config: PolicyAgentConfig, workspace_url: str = "", workspace_id: str = ""
) -> dict[str, Any]:
    storage = config.storage
    return {
        "storage": {
            "backend": storage.backend,
            "catalog": storage.catalog,
            "schema": storage.schema,
            "qualified_schema": storage.qualified_schema,
            "object_tags": dict(storage.object_tags),
        },
        "notifications": {
            "emails": list(config.notification_emails),
            "webhook_configured": bool(config.notification_webhook),
            "webhook": config.notification_webhook or "",
        },
        "resource_types": [rt.value for rt in supported_resource_types()],
        "operators": list(registered_operators()),
        "roles": [role.value for role in Role],
        "workspace_url": workspace_url,
        "workspace_id": workspace_id,
    }


def _workspace_url(workspace_client: Any) -> str:
    config = getattr(workspace_client, "config", None)
    return (getattr(config, "host", "") or "").rstrip("/")


def _workspace_id(workspace_client: Any) -> str:
    try:
        return str(workspace_client.get_workspace_id())
    except Exception:
        return ""


@router.get("")
def get_settings(
    config: PolicyAgentConfig = Depends(get_effective_config),
    workspace_client=Depends(get_workspace_client),
    _user: str = Depends(current_user),
) -> dict[str, Any]:
    """Return the effective deployment configuration (deploy-time defaults plus overrides)."""
    return _payload(config, _workspace_url(workspace_client), _workspace_id(workspace_client))


@router.put("")
def update_settings(
    body: SettingsUpdateRequest,
    _roles: set[Role] = Depends(require_admin),
    executor: SqlExecutor = Depends(get_executor),
    base_config: PolicyAgentConfig = Depends(get_config),
    workspace_client=Depends(get_workspace_client),
) -> dict[str, Any]:
    """Persist admin-editable overrides (object tags, notification destinations).

    The storage backend and schema are fixed at deploy time and are never changed here.
    """
    ensure_storage(executor, base_config.storage)
    if body.object_tags is not None:
        save_app_setting(
            executor, base_config.storage, SETTING_OBJECT_TAGS, json.dumps(body.object_tags)
        )
    if body.notification_emails is not None:
        save_app_setting(
            executor,
            base_config.storage,
            SETTING_NOTIFICATION_EMAILS,
            json.dumps(body.notification_emails),
        )
    if body.notification_webhook is not None:
        save_app_setting(
            executor, base_config.storage, SETTING_NOTIFICATION_WEBHOOK, body.notification_webhook
        )
    effective = apply_overrides(base_config, read_app_settings(executor, base_config.storage))
    return _payload(effective, _workspace_url(workspace_client), _workspace_id(workspace_client))
