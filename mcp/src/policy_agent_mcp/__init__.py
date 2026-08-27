"""Custom MCP server exposing the Databricks policy compliance framework.

The server is deployed as a Databricks App serving the streamable HTTP transport at
``/mcp`` so agents (for example a Genie space) can call the policy agent as a custom MCP
tool provider. Tool bodies live in :mod:`policy_agent_mcp.tools` and the FastMCP wiring in
:mod:`policy_agent_mcp.server`.
"""
