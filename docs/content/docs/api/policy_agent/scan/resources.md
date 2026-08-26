---
sidebar_label: resources
title: policy_agent.scan.resources
---

Fetches workspace resources and normalizes them into evaluable snapshots.

Each ``scan_*`` function reads one resource type from a `WorkspaceClient` and maps
every resource to the flat attribute set declared in
`policy_agent.policy.model.RESOURCE_ATTRIBUTES`. Missing SDK attributes degrade to
``None`` rather than raising, so a newer or older SDK still produces usable snapshots.

#### TASK\_DERIVED\_JOB\_ATTRIBUTES

Job attributes computed from a job's task definitions. Populating them requires listing
jobs with ``expand_tasks=True``, which fetches and deserializes every task — costly in large
workspaces — so callers should expand only when a policy actually reads one of these.

#### scan\_jobs

```python
def scan_jobs(workspace_client: WorkspaceClient,
              *,
              expand_tasks: bool = True) -> list[ResourceSnapshot]
```

Fetches and normalizes every job in the workspace.

**Arguments**:

- `workspace_client` - Databricks workspace client.
- `expand_tasks` - Whether to fetch full task definitions. Required to populate the
  `TASK_DERIVED_JOB_ATTRIBUTES`; when ``False`` those attributes are reported
  as ``None`` rather than a value guessed from tasks that were not fetched. Defaults
  to ``True`` so direct and inventory callers get complete snapshots.
  

**Returns**:

  A list of *ResourceSnapshots* for each job.

#### scan\_clusters

```python
def scan_clusters(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetches and normalizes every all-purpose cluster in the workspace.

**Arguments**:

- `workspace_client` - Databricks workspace client.
  

**Returns**:

  A list of *ResourceSnapshots* for each cluster.

#### scan\_sql\_warehouses

```python
def scan_sql_warehouses(
        workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetches and normalizes every SQL warehouse in the workspace.

**Arguments**:

- `workspace_client` - Databricks workspace client.
  

**Returns**:

  A list of *ResourceSnapshots* for each SQL warehouse.

#### scan\_apps

```python
def scan_apps(workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetches and normalizes every Databricks App in the workspace.

**Arguments**:

- `workspace_client` - Databricks workspace client.
  

**Returns**:

  A list of *ResourceSnapshots* for each app.

#### scan\_serving\_endpoints

```python
def scan_serving_endpoints(
        workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetches and normalizes every model serving endpoint in the workspace.

**Arguments**:

- `workspace_client` - Databricks workspace client.
  

**Returns**:

  A list of *ResourceSnapshots* for each serving endpoint.

#### scan\_pipelines

```python
def scan_pipelines(
        workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetches and normalizes every Spark Declarative pipeline in the workspace.

**Notes**:

  *list_pipelines* returns only summary attributes (e.g. name, creator, state). Because
  some attributes (e.g. catalog, edition, continuous, serverless) are part of the pipeline
  spec, each pipeline is fetched with *get()* to read its attributes.
  

**Arguments**:

- `workspace_client` - Databricks workspace client.
  

**Returns**:

  A list of *ResourceSnapshots* for each serving endpoint.

#### scan\_genie\_spaces

```python
def scan_genie_spaces(
        workspace_client: WorkspaceClient) -> list[ResourceSnapshot]
```

Fetches and normalizes every Genie space in the workspace.

**Arguments**:

- `workspace_client` - Databricks workspace client.
  

**Returns**:

  A list of *ResourceSnapshots* for each Genie space.

#### classify\_principal

```python
def classify_principal(identifier: str | None) -> str
```

Classifies a principal identifier as a service principal, user, or unknown.

**Arguments**:

- `identifier` - A principal identifier such as a user email or application id.
  

**Returns**:

  One of the ``OWNER_TYPE_*`` constants: ``service_principal`` for a UUID, ``user`` for an
  email-shaped value, and ``unknown`` for an empty identifier or any other value.

