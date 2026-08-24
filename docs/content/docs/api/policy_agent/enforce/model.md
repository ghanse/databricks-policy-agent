---
sidebar_label: model
title: policy_agent.enforce.model
---

Result types for the deployment-time enforcement gate.

The gate evaluates the same policies as a scan, but against resources *declared* in a
Databricks Asset Bundle rather than live workspace objects. Its verdict decides whether a
deployment pipeline should proceed.

## GateVerdict Objects

```python
class GateVerdict(str, Enum)
```

Outcome of an enforcement gate over a bundle.

## FixSuggestion Objects

```python
@dataclass(frozen=True)
class FixSuggestion()
```

A suggested remediation for one violating declared resource.

**Attributes**:

- `policy_name` - The violated policy.
- `resource_type` - Type of the declared resource.
- `resource_id` - Bundle key / name of the declared resource.
- `guidance` - Human-readable guidance (the policy's remediation text when available).

## GateResult Objects

```python
@dataclass(frozen=True)
class GateResult()
```

The outcome of gating a bundle's declared resources against policies.

**Attributes**:

- `verdict` - Overall gate verdict.
- `violations` - Every violating (policy, resource) evaluation.
- `blocking` - Violations that block the deployment.
- `overridden` - Soft violations waved through by an override.
- `warnings` - Violations below the fail-on threshold (never block).
- `fixes` - Suggested remediations (populated when fixes are requested).
- `override_reason` - Reason recorded for any overrides applied.

#### blocked

```python
@property
def blocked() -> bool
```

Whether the deployment should be blocked.

#### to\_dict

```python
def to_dict() -> dict[str, object]
```

Render a JSON-serialisable summary of the gate result.

**Returns**:

  A mapping suitable for machine-readable gate output.

