---
sidebar_label: resources
title: policy_agent.scan.resources
---

Fetch workspace resources and normalize them into evaluable snapshots.

Each ``scan_*`` function reads one resource type from a :class:`WorkspaceClient` and maps
every resource to the flat attribute set declared in
:data:`policy_agent.policy.model.RESOURCE_ATTRIBUTES`. Missing SDK attributes degrade to
``None`` rather than raising, so a newer or older SDK still produces usable snapshots.

#### TASK\_DERIVED\_JOB\_ATTRIBUTES

Job attributes computed from a job&#x27;s task definitions. Populating them requires listing
jobs with ``expand_tasks=True``, which fetches and deserializes every task — costly in large
workspaces — so callers should expand only when a policy actually reads one of these.

#### scan\_jobs

```python
def scan_jobs(workspace_client: WorkspaceClient,
              *,
              expand_tasks: bool = True) -> list[ResourceSnapshot]
```

Fetch and normalize every job in the workspace.

**Arguments**:

- `workspace_client` - An authenticated Databricks workspace client.
- `expand_tasks` - Whether to fetch full task definitions. Required to populate the
  :data:`TASK_DERIVED_JOB_ATTRIBUTES`; when ``False`` those attributes are reported
  as ``None`` rather than a value guessed from tasks that were not fetched. Defaults
  to ``True`` so direct and inventory callers get complete snapshots.
  

**Returns**:

  One snapshot per job.

#### scan\_clusters

```python
def scan_clusters(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetch and normalize every all-purpose cluster in the workspace.

**Arguments**:

- `workspace_client` - An authenticated Databricks workspace client.
  

**Returns**:

  One snapshot per cluster.

#### scan\_sql\_warehouses

```python
def scan_sql_warehouses(
        workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetch and normalize every SQL warehouse in the workspace.

**Arguments**:

- `workspace_client` - An authenticated Databricks workspace client.
  

**Returns**:

  One snapshot per SQL warehouse.

#### scan\_apps

```python
def scan_apps(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetch and normalize every Databricks App in the workspace.

**Arguments**:

- `workspace_client` - An authenticated Databricks workspace client.
  

**Returns**:

  One snapshot per app.

#### scan\_serving\_endpoints

```python
def scan_serving_endpoints(
        workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetch and normalize every model serving endpoint in the workspace.

**Arguments**:

- `workspace_client` - An authenticated Databricks workspace client.
  

**Returns**:

  One snapshot per serving endpoint.

#### classify\_principal

```python
def classify_principal(identifier: str | None) -> str
```

Classify a principal identifier as a service principal, user, or unknown.

**Arguments**:

- `identifier` - A principal identifier such as a user email or SP application id.
  

**Returns**:

  One of the ``OWNER_TYPE_*`` constants.

