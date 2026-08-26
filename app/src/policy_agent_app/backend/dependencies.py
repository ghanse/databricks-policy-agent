"""FastAPI dependencies exposing process-wide state built during app startup.

The workspace client, runtime configuration, and storage executor are created once in the
lifespan handler (see :mod:`app`) and stored on ``app.state``; these accessors read them so
routes stay decoupled from construction and tests can override them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request
from policy_agent.config import PolicyAgentConfig
from policy_agent.storage.backend import SqlExecutor

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient


def get_config(request: Request) -> PolicyAgentConfig:
    """Returns the runtime configuration built at startup.

    Args:
        request: The incoming request.

    Returns:
        The process-wide :class:`PolicyAgentConfig`.
    """
    return request.app.state.config


def get_executor(request: Request) -> SqlExecutor:
    """Returns the storage executor built at startup.

    Args:
        request: The incoming request.

    Returns:
        The process-wide :class:`SqlExecutor`.
    """
    return request.app.state.executor


def get_workspace_client(request: Request) -> WorkspaceClient:
    """Returns the workspace client built at startup.

    Args:
        request: The incoming request.

    Returns:
        The process-wide workspace client.
    """
    return request.app.state.workspace_client
