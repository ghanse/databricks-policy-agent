---
sidebar_label: runner
title: policy_agent.jobs.runner
---

Shared scan-and-persist logic for the provisioned jobs.

``run_policy_scan`` is the single place that runs a scan, writes results, reconciles the
remediation cycle, and notifies — so the ad-hoc scan job and the scheduled scan job behave
identically apart from how they are triggered.

#### run\_policy\_scan

```python
def run_policy_scan(workspace_client: WorkspaceClient,
                    executor: SqlExecutor,
                    config: PolicyAgentConfig,
                    policies: Iterable[Policy],
                    triggered_by: str,
                    resource_types: Iterable[ResourceType] | None = None,
                    dry_run: bool = False) -> ScanResult
```

Run a scan and, unless ``dry_run``, persist results and reconcile remediations.

**Arguments**:

- `workspace_client` - An authenticated Databricks workspace client.
- `executor` - The storage executor.
- `config` - The runtime configuration.
- `policies` - The policies to evaluate.
- `triggered_by` - Label recorded as the scan's initiator.
- `resource_types` - Optional restriction on scanned resource types.
- `dry_run` - When ``True`` the scan runs but nothing is written or notified.
  

**Returns**:

  The completed `ScanResult`.

#### execute\_scan\_job

```python
def execute_scan_job(triggered_by: str) -> int
```

Run a full scan of every approved policy from the environment configuration.

Builds the workspace client and storage executor from the ambient environment (as set by
the Databricks Asset Bundle), scans all approved policies, and persists the outcome.

**Arguments**:

- `triggered_by` - Label recorded as the scan's initiator.
  

**Returns**:

  Process exit code: ``0`` on success, ``1`` on error.

