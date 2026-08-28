# Policy Agent MCP server

A custom [MCP](https://docs.databricks.com/aws/en/agents/mcp-tools/custom-mcp) server that exposes
the policy compliance framework to Databricks agents (including Genie spaces). It is deployed as a
Databricks App serving the streamable HTTP transport at `/mcp`, and reuses the `policy_agent`
library and its stored state.

## Layout
- `src/policy_agent_mcp/tools.py` — tool implementations (pure functions of a `ServerContext`).
- `src/policy_agent_mcp/server.py` — FastMCP wiring and the `main()` entry point.
- `src/policy_agent_mcp/context.py` — lazily-built workspace/config/storage context.
- `scripts/build_app.py` — assembles the deployable app tree under `mcp/.build`.

## Develop
```bash
make mcp-install   # uv sync --group dev
make mcp-lint      # ruff + mypy
make mcp-test      # pytest
```

## Run locally
```bash
cd mcp && uv run python -m policy_agent_mcp.server   # serves /mcp on 0.0.0.0:8000
```

## Deploy
The server deploys with the rest of the framework through the root `databricks.yml` bundle as the
`mcp-policy-agent` app. See the [MCP Server](../docs/content/docs/mcp.mdx) docs and
[Deployment](../docs/content/docs/deployment.mdx).

```bash
cd mcp && uv run python scripts/build_app.py && cd ..
databricks bundle deploy -t dev -p <profile>
```

> **Note:** `mcp/uv.lock` is generated with `make lock-mcp-dependencies` from an environment with
> access to the package index; regenerate it there when changing dependencies.
