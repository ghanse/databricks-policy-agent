---
sidebar_position: 6
---

# Storage

Policy-agent state — policies, versions, scans, findings, remediations, approval events,
schedules, and role mappings — is persisted through a backend-agnostic executor. Two
interchangeable backends implement the same `SqlExecutor` surface:

- **Unity Catalog Delta** (`DeltaSqlExecutor`) — runs SQL through a SQL warehouse via the
  Statement Execution API. Requires a `catalog` and `schema`.
- **Lakebase Postgres** (`LakebaseSqlExecutor`) — runs SQL through a SQLAlchemy engine.
  Requires the `lakebase` extra and a connection URL.

```python
from policy_agent.storage import StorageConfig, DeltaSqlExecutor, ensure_storage, save_policy

config = StorageConfig(backend="uc", catalog="governance", schema="policy_agent",
                       object_tags={"team": "platform"})
executor = DeltaSqlExecutor(workspace_client, warehouse_id="…")
ensure_storage(executor, config)   # creates the catalog/schema and tables if absent
```

`ensure_storage` creates the catalog/schema (UC) or schema (Postgres) and every table if
they do not already exist — satisfying the "selected or new" requirement.

## Object tagging

Every configured tag in `StorageConfig.object_tags` is applied to created schemas and tables
(as UC tags or a Postgres comment) and stamped onto every stored row, so all objects the
agent owns are discoverable and auditable. A `managed_by=policy-agent` marker tag is always
present.

## Configuration

Both the app and the jobs read configuration from `POLICY_AGENT_*` environment variables via
`config_from_env`. See [Deployment](deployment.md) for the full list.
