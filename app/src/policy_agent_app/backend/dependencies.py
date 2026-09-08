"""FastAPI dependencies exposing process-wide state built during app startup.

The workspace client, runtime configuration, and storage executor are created once in the
lifespan handler (see :mod:`app`) and stored on ``app.state``; these accessors read them so
routes stay decoupled from construction and tests can override them.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import TYPE_CHECKING

from fastapi import Request
from policy_agent.config import PolicyAgentConfig
from policy_agent.storage.backend import SqlExecutor, read_app_settings
from policy_agent.tagging import managed_tags

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

# Keys under which admin-editable overrides are persisted in the ``app_settings`` table.
SETTING_OBJECT_TAGS = "object_tags"
SETTING_NOTIFICATION_EMAILS = "notification_emails"
SETTING_NOTIFICATION_WEBHOOK = "notification_webhook"


def get_config(request: Request) -> PolicyAgentConfig:
    """Return the runtime configuration built at startup.

    Args:
        request: The incoming request.

    Returns:
        The process-wide :class:`PolicyAgentConfig`.
    """
    return request.app.state.config


def get_effective_config(request: Request) -> PolicyAgentConfig:
    """Return the runtime configuration with admin-set overrides layered on top.

    Object tags and notification destinations an administrator saves through the app are
    persisted in ``app_settings`` and applied here over the deploy-time defaults. The storage
    backend and schema are never overridden — they are fixed at deploy time. A missing or
    unreadable settings table falls back to the base configuration.

    Args:
        request: The incoming request.

    Returns:
        The effective :class:`PolicyAgentConfig`.
    """
    base: PolicyAgentConfig = request.app.state.config
    executor: SqlExecutor = request.app.state.executor
    try:
        overrides = read_app_settings(executor, base.storage)
    except Exception:
        return base
    return apply_overrides(base, overrides)


def apply_overrides(base: PolicyAgentConfig, overrides: dict[str, str]) -> PolicyAgentConfig:
    """Layer stored overrides onto a base configuration.

    Args:
        base: The deploy-time configuration.
        overrides: Raw text values keyed by ``SETTING_*``.

    Returns:
        The configuration with any provided overrides applied.
    """
    storage = base.storage
    emails = base.notification_emails
    webhook = base.notification_webhook
    # Each override is parsed independently and defensively: a corrupted or malformed row
    # falls back to the deploy-time value rather than breaking every request that reads the
    # effective config.
    tags_raw = overrides.get(SETTING_OBJECT_TAGS)
    if tags_raw:
        try:
            parsed = json.loads(tags_raw)
            tags = managed_tags({str(k): str(v) for k, v in parsed.items()})
            storage = replace(storage, object_tags=tags)
        except (ValueError, AttributeError):
            pass
    emails_raw = overrides.get(SETTING_NOTIFICATION_EMAILS)
    if emails_raw:
        try:
            emails = tuple(str(e) for e in json.loads(emails_raw))
        except ValueError:
            pass
    if SETTING_NOTIFICATION_WEBHOOK in overrides:
        webhook = overrides[SETTING_NOTIFICATION_WEBHOOK] or None
    return replace(base, storage=storage, notification_emails=emails, notification_webhook=webhook)


def get_executor(request: Request) -> SqlExecutor:
    """Return the storage executor built at startup.

    Args:
        request: The incoming request.

    Returns:
        The process-wide :class:`SqlExecutor`.
    """
    return request.app.state.executor


def get_workspace_client(request: Request) -> WorkspaceClient:
    """Return the workspace client built at startup.

    Args:
        request: The incoming request.

    Returns:
        The process-wide workspace client.
    """
    return request.app.state.workspace_client


def get_user_workspace_client(request: Request) -> WorkspaceClient:
    """Return a workspace client authenticated as the calling user (on-behalf-of).

    Databricks Apps forward the signed-in user's access token in ``X-Forwarded-Access-Token``
    when user authorization is enabled. Building a client from it means writes are made with
    the user's own permissions and attributed to them, within the app's granted scopes. When
    the header is absent (local development, or OBO not enabled) this falls back to the
    process-wide service-principal client.

    Args:
        request: The incoming request.

    Returns:
        A user-scoped workspace client, or the service-principal client as a fallback.
    """
    from databricks.sdk import WorkspaceClient

    sp_client = request.app.state.workspace_client
    token = request.headers.get("X-Forwarded-Access-Token")
    if not token:
        return sp_client
    host = getattr(getattr(sp_client, "config", None), "host", None)
    # ``auth_type="pat"`` forces bearer-token auth for the forwarded user token. Without it the
    # SDK also picks up the app service principal's ambient DATABRICKS_CLIENT_ID/SECRET and
    # fails with "more than one authorization method configured".
    return WorkspaceClient(host=host, token=token, auth_type="pat")
