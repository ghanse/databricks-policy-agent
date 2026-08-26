---
sidebar_label: engine
title: policy_agent.scan.engine
---

The scan orchestrator — the primary public entry point for running compliance scans.

``run_scan`` fetches each relevant resource type once, evaluates every applicable policy
against every resource, and returns an immutable `ScanResult`. It is a pure function
of the workspace state and the supplied policies, which makes it equally usable from ad-hoc
code, a scheduled job, or the app's API.

#### run\_scan

```python
def run_scan(
        workspace_client: WorkspaceClient,
        policies: Iterable[Policy],
        resource_types: Iterable[ResourceType] | None = None) -> ScanResult
```

Scans the workspace for compliance with the given policies.

Only resource types that both appear in ``policies`` and (when provided) in
``resource_types`` are fetched, so a scan never calls an API it does not need.

**Arguments**:

- `workspace_client` - An authenticated Databricks workspace client.
- `policies` - The policies to evaluate. Each is validated before use.
- `resource_types` - Optional restriction on which resource types to scan; when ``None``
  every resource type referenced by ``policies`` is scanned.
  

**Returns**:

  A `ScanResult` containing one finding per applicable (policy, resource) pair.
  

**Raises**:

- `InvalidPolicyError` - If any supplied policy fails validation.
- `UnknownConditionError` - If any policy references an unregistered operator.

#### collect\_snapshots

```python
def collect_snapshots(
    workspace_client: WorkspaceClient, resource_types: Iterable[ResourceType]
) -> dict[ResourceType, list[ResourceSnapshot]]
```

Fetches resource snapshots without evaluating any policy.

Useful for inventory views and dry runs where only the normalized resource attributes
are needed.

**Arguments**:

- `workspace_client` - An authenticated Databricks workspace client.
- `resource_types` - The resource types to fetch.
  

**Returns**:

  A mapping from each requested resource type to its snapshots.

