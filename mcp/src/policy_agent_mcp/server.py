"""FastMCP server exposing the policy agent as a custom MCP server.

Deployed as a Databricks App serving the streamable HTTP transport at ``/mcp``. The tool
bodies live in :mod:`policy_agent_mcp.tools` so they can be unit-tested without the MCP
runtime; here each is registered and, where it needs workspace or storage access, bound to
the process-wide `ServerContext`.

Run locally with ``python -m policy_agent_mcp.server`` (or the ``policy-agent-mcp`` script);
the Databricks App runtime launches the same entry point via ``app.yaml``.
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from policy_agent_mcp import tools
from policy_agent_mcp.context import get_context

mcp = FastMCP("policy-agent")


@mcp.tool()
def list_resource_types() -> list[dict[str, Any]]:
    """List every resource type a policy can target, with its attributes and capabilities."""
    return tools.list_resource_types()


@mcp.tool()
def describe_resource_type(resource_type: str) -> dict[str, Any]:
    """Describe a single resource type: its attributes and whether it is scannable/taggable."""
    return tools.describe_resource_type(resource_type)


@mcp.tool()
def list_operators() -> list[str]:
    """List the comparison operators available for policy conditions."""
    return tools.list_operators()


@mcp.tool()
def list_policies(status: str | None = "approved") -> list[dict[str, Any]]:
    """List stored policies, by default only the approved ones (pass ``all`` for every policy)."""
    return tools.list_policies(get_context(), status)


@mcp.tool()
def get_policy(name: str) -> dict[str, Any]:
    """Get a single stored policy by name."""
    return tools.get_policy(get_context(), name)


@mcp.tool()
def run_compliance_scan(
    resource_types: list[str] | None = None,
    policy_names: list[str] | None = None,
) -> dict[str, Any]:
    """Run a live compliance scan of the approved policies and return a summary and violations.

    The scan reads the workspace but persists nothing. Optionally restrict it to specific
    resource types or policy names.
    """
    return tools.run_compliance_scan(get_context(), resource_types, policy_names)


@mcp.tool()
def list_recent_scans(limit: int = 20) -> list[dict[str, Any]]:
    """List recent persisted scans (id, timing, counts), most recent first."""
    return tools.list_recent_scans(get_context(), limit)


@mcp.tool()
def get_scan_findings(scan_id: str) -> list[dict[str, Any]]:
    """Get the findings recorded for a single persisted scan."""
    return tools.get_scan_findings(get_context(), scan_id)


def main() -> None:
    """Serves the MCP server over the streamable HTTP transport.

    Binds the host and port the Databricks App runtime provides (falling back to
    ``0.0.0.0:8000``, the platform default) and serves the ``/mcp`` endpoint.
    """
    mcp.settings.host = os.environ.get("MCP_HOST", "0.0.0.0")
    mcp.settings.port = int(
        os.environ.get("DATABRICKS_APP_PORT") or os.environ.get("PORT") or "8000"
    )
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
