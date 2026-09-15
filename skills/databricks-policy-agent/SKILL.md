---
name: databricks-policy-agent
description: "Author, validate, scan, and enforce Databricks Policy Agent compliance policies. Use when writing allow/deny policies over Databricks workspace objects (jobs, clusters, SQL warehouses, apps, serving endpoints, Unity Catalog objects, pipelines, and more), running a compliance scan against a workspace, interpreting findings and remediations, or gating a Databricks Asset Bundle before deployment with the `policy-agent` CLI or the `policy_agent` Python library."
---

# Databricks Policy Agent

## Overview

The Policy Agent declares **allow**/**deny** compliance policies over Databricks workspace
objects, scans a workspace for violations, tracks them through a remediation cycle, and gates
policy-affecting bundle deployments. Policies are pure data — a condition tree over a resource's
attributes — so no policy runs arbitrary code, and validation rejects unknown attributes or
operators at author time.

Three surfaces run the same library:

- **`policy-agent` CLI** — `validate`, `scan`, and `enforce`.
- **Python library** (`policy_agent`) — `run_scan`, `run_policy_scan`, the policy model, and
  the storage/approval/remediation state machines.
- **Databricks App + provisioned jobs** — an authoring/review UI and on-demand/scheduled scans.

## When to use this skill

- Writing or reviewing policy YAML (or the Python DSL) — see **[authoring.md](authoring.md)**.
- Running a compliance scan and reading the results — see **[scanning.md](scanning.md)**.
- Blocking a bundle deploy that would introduce a violation — see **[enforcement.md](enforcement.md)**.

## The three verbs

```bash
# 1. Validate policy files offline (no workspace needed).
uv run policy-agent validate examples/

# 2. Scan a live workspace against policy files; --dry-run writes nothing.
uv run policy-agent scan --profile <profile> --policies examples/ --dry-run

# 3. Gate a bundle's declared resources before deploy (exit 1 = blocked).
uv run policy-agent enforce --bundle . --target dev --policies examples/
```

Run against the stored, **approved** policies instead of files by omitting `--policies`; that
path reads from configured storage and needs the `POLICY_AGENT_*` environment set (see
[scanning.md](scanning.md)).

## A policy at a glance

```yaml
policy: production-jobs-need-failure-alerts
description: Production jobs must configure on-failure email notifications.
resource_type: job
effect: allow                     # allow = compliant only when the rule matches
enforcement_level: hard           # advisory | soft | hard
match:                            # optional selector: which resources this applies to
  all:
    - { attribute: name, operator: matches_regex, value: "^prod_.+$" }
rule:                             # the compliance condition
  all:
    - { attribute: has_email_notifications, operator: equals, value: true }
remediation: Add an on-failure email notification to the job.
```

- **`effect: allow`** → a resource is compliant only when `rule` matches (allow-list).
- **`effect: deny`** → a resource is a violation when `rule` matches (deny-list).
- **`match`** narrows the population; a resource the `match` excludes yields no finding at all.
- **`enforcement_level`** sets how strongly the policy blocks a deploy gate: `advisory` reports
  only, `soft` blocks but can be overridden with a recorded reason, `hard` blocks and cannot.

The `examples/` directory ships one policy file per resource type — copy from there.

## Reference files

- **[authoring.md](authoring.md)** — the full policy schema, condition operators, every resource
  type and its evaluable attributes, the Python DSL, and validation.
- **[scanning.md](scanning.md)** — running scans from the CLI and the library, the
  `POLICY_AGENT_*` configuration, storage backends, and reading `ScanResult` findings.
- **[enforcement.md](enforcement.md)** — bundle gating: thresholds, overrides, fix suggestions,
  and output formats.
