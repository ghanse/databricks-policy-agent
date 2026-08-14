---
sidebar_position: 5
---

# Scanning

`run_scan` is the primary entry point. It fetches each relevant resource type once,
evaluates every applicable policy against every resource, and returns an immutable
`ScanResult`.

```python
from databricks.sdk import WorkspaceClient
from policy_agent import run_scan, load_policies_from_yaml

policies = load_policies_from_yaml("examples/")
result = run_scan(WorkspaceClient(), policies)

summary = result.summary()
print(summary.evaluated, summary.violations, summary.compliance_rate)
for finding in result.violations:
    print(finding.severity, finding.policy_name, finding.resource_name)
```

A scan only fetches resource types that appear in the supplied policies (and, if given, in
the `resource_types` restriction), so it never calls an API it does not need.

## Adding a resource type

Scanning is backed by a registry. To support a new resource type:

1. Add the type to `ResourceType` and its attribute set to `RESOURCE_ATTRIBUTES`
   (`policy_agent.policy.model`).
2. Write a `scan_*` function that normalises the resource to a `ResourceSnapshot`
   (`policy_agent.scan.resources`).
3. Register it in `RESOURCE_SCANNERS` (`policy_agent.scan.registry`).

## Ways to run a scan

- **Ad hoc** in Python via `run_scan`.
- **CLI:** `policy-agent scan --profile <profile> [--policies <path>] [--dry-run]`.
- **App API:** `POST /api/v1/scans`.
- **Jobs:** the provisioned on-demand and scheduled scan jobs.
