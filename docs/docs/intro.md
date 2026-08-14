---
sidebar_position: 1
slug: /
---

# Databricks Policy Agent

The Policy Agent is a compliance framework for Databricks workspace objects. It lets teams
declare **allow** and **deny** policies over Jobs, Clusters, SQL Warehouses, Apps, and Model
Serving Endpoints; scan the workspace for compliance; track violations through a remediation
cycle; and gate policy changes behind a draft → review → approve workflow.

It ships as three coordinated pieces:

1. **A Python library** (`policy_agent`) — the pure, functional core: the policy model, the
   scan engine, configurable storage, and the approval and remediation state machines.
2. **A Databricks App** — a FastAPI JSON API and a React single-page app for authoring
   policies, running scans, reviewing findings, and approving policy changes.
3. **Provisioned jobs** — on-demand and scheduled scans that persist results and reconcile
   the remediation cycle.

## Quick start

```bash
uv sync --all-extras

# Validate policy files
uv run policy-agent validate examples/

# Dry-run a scan against a workspace (no writes)
uv run policy-agent scan --profile my-profile --policies examples/ --dry-run
```

```python
from databricks.sdk import WorkspaceClient
from policy_agent import load_policies_from_yaml, run_scan

policies = load_policies_from_yaml("examples/clusters.yaml")
result = run_scan(WorkspaceClient(), policies)
print(result.summary())
```

Continue with [Concepts](concepts.md) to understand the model, or jump to
[Policy syntax](policy-syntax.md) to start authoring.
