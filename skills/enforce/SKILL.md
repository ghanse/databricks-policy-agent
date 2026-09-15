---
name: enforce
description: "Gate a Databricks Asset Bundle's declared resources against Policy Agent policies before deployment. Use when running the `policy-agent enforce` CLI as a pre-deploy check in CI, setting the fail-on enforcement threshold, overriding soft violations with a recorded reason, or emitting fix suggestions and JSON output. To write policies see policy-agent:author; to scan a live workspace see policy-agent:scan."
---

# Enforcing policies on a bundle

`enforce` gates a Databricks Asset Bundle's **declared** resources against policies *before* it
deploys, so a non-compliant resource is caught at deploy time rather than by a later scan. It
evaluates the bundle's resolved configuration — no workspace resources are fetched — so any resource
type a policy targets can be gated, including types that are never live-scanned. Author the policies
first with **policy-agent:author**.

```bash
uv run policy-agent enforce --bundle . --target dev --policies examples/
```

The command exits `1` when the gate is blocked and `0` otherwise, so it drops into CI as a pre-deploy
check.

## Flags

| Flag | Meaning |
| --- | --- |
| `--bundle` | Bundle directory, or a resolved `bundle validate` JSON file (default `.`). |
| `--target` | Bundle target to resolve. |
| `--policies` | Policy file or directory; omit to use the stored *approved* policies. |
| `--fail-on` | Minimum enforcement level that blocks: `advisory`, `soft`, or `hard` (default `hard`). |
| `--override` | Policy name to override; **soft violations only**. Repeatable. |
| `--override-reason` | Reason recorded for overrides; **required** whenever `--override` is used. |
| `--fix` | Include suggested remediations for violations. |
| `--output` | `text` (default) or `json`. |

## How the gate decides

Each violation is sorted by its policy's enforcement level against `--fail-on`:

- **blocking** — a violation at or above the `--fail-on` threshold that is not overridden.
- **overridden** — a *soft* violation named in `--override` (with a reason). Hard violations can
  never be overridden.
- **warnings** — violations below the threshold.

The gate is **blocked** when any blocking violations remain. Text output prints the verdict and
counts followed by each finding (`BLOCK`/`OVERRIDE`/`WARN`), plus `FIX` lines when `--fix` is set.
`--output json` emits the same result as a structured object for CI to parse.

## Examples

```bash
# Block only on hard violations (the default); report the rest.
uv run policy-agent enforce --bundle . --target prod --policies policies/

# Also block on soft, but let one named soft policy through with a reason.
uv run policy-agent enforce --bundle . --target prod --policies policies/ \
  --fail-on soft \
  --override jobs-should-use-serverless-compute \
  --override-reason "Legacy ETL migrates to serverless next sprint"

# Machine-readable output with remediation hints, for a CI step.
uv run policy-agent enforce --bundle . --target dev --policies policies/ --fix --output json
```

Enforcement and scanning share one policy model, so a policy behaves identically whether it gates a
bundle here or evaluates live resources in a scan (**policy-agent:scan**). Ready-made example
policies are in [`examples/`](https://github.com/ghanse/databricks-policy-agent/tree/main/examples).
