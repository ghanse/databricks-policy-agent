# Scanning a workspace

A scan fetches each resource type a policy references, evaluates every applicable policy against
every resource, and returns a `ScanResult` — one `Finding` per (policy, resource) pair. A scan
only fetches the resource types its policies reference, so it never calls an API it does not need.

## From the CLI

```bash
uv run policy-agent scan --profile <profile> --policies examples/ --dry-run
```

| Flag | Meaning |
| --- | --- |
| `--profile` | Databricks CLI profile to authenticate with (omit to use the default). |
| `--policies` | Policy file or directory; **omit** to scan the stored *approved* policies. |
| `--resource-types` | Comma-separated types to restrict the scan to, e.g. `job,cluster`. |
| `--dry-run` | Evaluate without writing results or notifying. |

The summary line reports evaluated / violation counts and a compliance rate, then lists each
violation as `[<enforcement_level>] <policy> -> <resource>`.

Omitting `--policies` reads the approved policies from configured storage, which requires the
`POLICY_AGENT_*` environment (below). With `--policies`, a `--dry-run` needs only workspace
access; without `--dry-run` it also persists results and reconciles remediations.

## From the library

```python
from databricks.sdk import WorkspaceClient
from policy_agent.policy.yaml_loader import load_policies_from_yaml
from policy_agent.scan.engine import run_scan

ws = WorkspaceClient()
policies = load_policies_from_yaml("examples/jobs.yaml")
result = run_scan(ws, policies, resource_types=None)   # None = every type the policies reference
```

`run_scan(workspace_client, policies, resource_types=None)` is a pure function of workspace state
and the policies — it validates each policy, fetches, evaluates, and returns a `ScanResult`
without writing anything. Use it for ad-hoc checks, dry runs, and notebooks.

To also persist results and reconcile the remediation cycle, use
`run_policy_scan(workspace_client, executor, config, policies, triggered_by, resource_types=None,
dry_run=False)` from `policy_agent.jobs.runner`, building `config` and `executor` from the
environment:

```python
from policy_agent.config import config_from_env, create_executor
from policy_agent.jobs.runner import run_policy_scan

config = config_from_env()
executor = create_executor(config, ws)
result = run_policy_scan(ws, executor, config, policies, triggered_by="notebook")
```

## Configuration (`POLICY_AGENT_*`)

`config_from_env()` reads these environment variables (the Asset Bundle sets them for the app and
jobs, so a single call configures every runtime):

| Variable | Purpose |
| --- | --- |
| `POLICY_AGENT_STORAGE_BACKEND` | `unity_catalog` (default) or the Lakebase backend. |
| `POLICY_AGENT_CATALOG` / `POLICY_AGENT_SCHEMA` | Delta storage location (schema defaults to `policy_agent`). |
| `POLICY_AGENT_TABLE_PREFIX` | Optional prefix on the state tables. |
| `POLICY_AGENT_WAREHOUSE_ID` | SQL warehouse id — **required** for the Unity Catalog backend. |
| `POLICY_AGENT_LAKEBASE_URL` | SQLAlchemy URL — **required** for the Lakebase backend. |
| `POLICY_AGENT_TAGS` | Tags stamped on created schemas/tables and every row. |
| `POLICY_AGENT_NOTIFICATION_EMAILS` | Comma-separated recipients for scan outcomes. |
| `POLICY_AGENT_NOTIFICATION_WEBHOOK` | Optional webhook posted with scan summaries. |

`create_executor` raises `StorageError` if the backend's required connection setting is missing.
A pure `run_scan` (or a `--dry-run`) needs none of this — only workspace access.

## Reading the result

`ScanResult` exposes:

- `result.summary()` → a `ScanSummary` with `evaluated`, `compliant`, `violations`,
  `compliance_rate`, and violation counts broken down by enforcement level and resource type.
- `result.violations` → only the non-compliant findings.
- `result.findings` → every evaluation.

Each `Finding` carries `policy_name`, `resource_type`, `resource_id`, `resource_name`,
`compliant`, `effect`, `enforcement_level`, `message`, `remediation`, and `owner`.

```python
s = result.summary()
print(f"{s.violations} violations across {s.evaluated} checks ({s.compliance_rate:.0%} compliant)")
for finding in result.violations:
    print(f"[{finding.enforcement_level.value}] {finding.policy_name} -> {finding.resource_name}")
```

The `examples/` directory includes a runnable scanning notebook, and the `docs/` scanning guide
covers the full storage and jobs setup.
