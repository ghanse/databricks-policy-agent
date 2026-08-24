---
sidebar_label: config
title: policy_agent.config
---

Runtime configuration assembled from environment variables.

The app and the provisioned jobs are configured entirely through environment variables set
by the Databricks Asset Bundle, so a single `config_from_env` call yields everything
needed to build a storage executor and send notifications.

## PolicyAgentConfig Objects

```python
@dataclass(frozen=True)
class PolicyAgentConfig()
```

Everything the app and jobs need to reach storage and send notifications.

**Attributes**:

- `storage` - Where policy-agent state is persisted.
- `warehouse_id` - SQL warehouse id for the Unity Catalog Delta backend.
- `lakebase_url` - SQLAlchemy URL for the Lakebase Postgres backend.
- `notification_emails` - Recipients notified about scan outcomes.
- `notification_webhook` - Optional webhook posted with scan summaries.

#### config\_from\_env

```python
def config_from_env(
        environ: Mapping[str, str] | None = None) -> PolicyAgentConfig
```

Build a `PolicyAgentConfig` from environment variables.

**Arguments**:

- `environ` - Environment mapping to read; defaults to ``os.environ``.
  

**Returns**:

  The assembled configuration, with the managed marker tag always applied.

#### create\_executor

```python
def create_executor(config: PolicyAgentConfig,
                    workspace_client: WorkspaceClient) -> SqlExecutor
```

Build the SQL executor for the configured storage backend.

**Arguments**:

- `config` - The runtime configuration.
- `workspace_client` - An authenticated Databricks workspace client.
  

**Returns**:

  A `SqlExecutor` for the configured backend.
  

**Raises**:

- `StorageError` - If the backend's required connection setting is missing.

