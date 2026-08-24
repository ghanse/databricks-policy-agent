"""Runtime configuration assembled from environment variables.

The app and the provisioned jobs are configured entirely through environment variables set
by the Databricks Asset Bundle, so a single `config_from_env` call yields everything
needed to build a storage executor and send notifications.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from policy_agent.errors import StorageError
from policy_agent.storage.config import BACKEND_UNITY_CATALOG, StorageConfig
from policy_agent.storage.delta import DeltaSqlExecutor
from policy_agent.tagging import managed_tags, parse_tags

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

    from policy_agent.storage.backend import SqlExecutor

ENV_STORAGE_BACKEND = "POLICY_AGENT_STORAGE_BACKEND"
ENV_CATALOG = "POLICY_AGENT_CATALOG"
ENV_SCHEMA = "POLICY_AGENT_SCHEMA"
ENV_TABLE_PREFIX = "POLICY_AGENT_TABLE_PREFIX"
ENV_TAGS = "POLICY_AGENT_TAGS"
ENV_WAREHOUSE_ID = "POLICY_AGENT_WAREHOUSE_ID"
ENV_LAKEBASE_URL = "POLICY_AGENT_LAKEBASE_URL"
ENV_NOTIFICATION_EMAILS = "POLICY_AGENT_NOTIFICATION_EMAILS"
ENV_NOTIFICATION_WEBHOOK = "POLICY_AGENT_NOTIFICATION_WEBHOOK"


@dataclass(frozen=True)
class PolicyAgentConfig:
    """Everything the app and jobs need to reach storage and send notifications.

    Attributes:
        storage: Where policy-agent state is persisted.
        warehouse_id: SQL warehouse id for the Unity Catalog Delta backend.
        lakebase_url: SQLAlchemy URL for the Lakebase Postgres backend.
        notification_emails: Recipients notified about scan outcomes.
        notification_webhook: Optional webhook posted with scan summaries.
    """

    storage: StorageConfig
    warehouse_id: str | None = None
    lakebase_url: str | None = None
    notification_emails: tuple[str, ...] = ()
    notification_webhook: str | None = None


def config_from_env(environ: Mapping[str, str] | None = None) -> PolicyAgentConfig:
    """Build a `PolicyAgentConfig` from environment variables.

    Args:
        environ: Environment mapping to read; defaults to ``os.environ``.

    Returns:
        The assembled configuration, with the managed marker tag always applied.
    """
    env = os.environ if environ is None else environ
    storage = StorageConfig(
        backend=env.get(ENV_STORAGE_BACKEND, BACKEND_UNITY_CATALOG),
        catalog=env.get(ENV_CATALOG),
        schema=env.get(ENV_SCHEMA, "policy_agent"),
        table_prefix=env.get(ENV_TABLE_PREFIX, ""),
        object_tags=managed_tags(parse_tags(env.get(ENV_TAGS, ""))),
    )
    return PolicyAgentConfig(
        storage=storage,
        warehouse_id=env.get(ENV_WAREHOUSE_ID),
        lakebase_url=env.get(ENV_LAKEBASE_URL),
        notification_emails=_split(env.get(ENV_NOTIFICATION_EMAILS, "")),
        notification_webhook=env.get(ENV_NOTIFICATION_WEBHOOK),
    )


def create_executor(config: PolicyAgentConfig, workspace_client: WorkspaceClient) -> SqlExecutor:
    """Build the SQL executor for the configured storage backend.

    Args:
        config: The runtime configuration.
        workspace_client: An authenticated Databricks workspace client.

    Returns:
        A `SqlExecutor` for the configured backend.

    Raises:
        StorageError: If the backend's required connection setting is missing.
    """
    if config.storage.is_unity_catalog:
        if not config.warehouse_id:
            raise StorageError(f"Unity Catalog storage requires {ENV_WAREHOUSE_ID}.")
        return DeltaSqlExecutor(workspace_client, config.warehouse_id)
    if not config.lakebase_url:
        raise StorageError(f"Lakebase storage requires {ENV_LAKEBASE_URL}.")
    from sqlalchemy import create_engine

    from policy_agent.storage.lakebase import LakebaseSqlExecutor

    return LakebaseSqlExecutor(create_engine(config.lakebase_url))


def _split(raw: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw.split(",") if item.strip())
