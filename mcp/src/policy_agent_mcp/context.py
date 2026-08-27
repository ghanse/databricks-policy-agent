"""Lazily-built process context shared by the MCP tools.

The workspace client, runtime configuration, and storage executor are built once on first
use and cached, mirroring the app's lifespan wiring. Tools take a `ServerContext`
argument so they stay pure and testable with fakes; the FastMCP layer supplies the real one
from `get_context`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from policy_agent.config import PolicyAgentConfig, config_from_env, create_executor

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient
    from policy_agent.storage.backend import SqlExecutor


@dataclass(frozen=True)
class ServerContext:
    """Everything the MCP tools need to reach the workspace and stored policy state.

    Attributes:
        config: The runtime configuration built from environment variables.
        workspace_client: An authenticated Databricks workspace client.
        executor: The storage executor for the configured backend.
    """

    config: PolicyAgentConfig
    workspace_client: WorkspaceClient
    executor: SqlExecutor


_context: ServerContext | None = None


def build_context() -> ServerContext:
    """Builds a fresh `ServerContext` from the environment.

    Returns:
        A context wired to the configured storage backend and a default workspace client.
    """
    from databricks.sdk import WorkspaceClient

    config = config_from_env()
    workspace_client = WorkspaceClient()
    executor = create_executor(config, workspace_client)
    return ServerContext(config=config, workspace_client=workspace_client, executor=executor)


def get_context() -> ServerContext:
    """Returns the process-wide context, building it on first use.

    Returns:
        The cached `ServerContext`.
    """
    global _context
    if _context is None:
        _context = build_context()
    return _context
