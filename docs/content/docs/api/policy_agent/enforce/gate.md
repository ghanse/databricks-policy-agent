---
sidebar_label: gate
title: policy_agent.enforce.gate
---

Evaluate declared bundle resources against policies and decide a gate verdict.

The gate reuses the scan evaluator (:func:`evaluate_resource`) — the only difference from a
live scan is the source of the snapshots. Enforcement levels decide the verdict: ``advisory``
violations only warn, ``soft`` violations block unless overridden, and ``hard`` violations
block and cannot be overridden.

#### run\_gate

```python
def run_gate(policies: Iterable[Policy],
             snapshots: Iterable[ResourceSnapshot],
             *,
             fail_on: EnforcementLevel = EnforcementLevel.HARD,
             overrides: frozenset[str] = frozenset(),
             override_reason: str = "",
             suggest_remediations: bool = False) -> GateResult
```

Gate declared resources against policies.

**Arguments**:

- `policies` - The policies to enforce.
- `snapshots` - Declared-resource snapshots (see :func:`snapshot_bundle`).
- `fail_on` - Minimum enforcement level that blocks (``advisory`` blocks everything,
  ``hard`` blocks only hard violations).
- `overrides` - Policy names to override; only ``soft`` violations can be overridden.
- `snapshots`1 - Reason recorded for the overrides.
- `snapshots`2 - When ``True``, attach remediation suggestions for violations.
  

**Returns**:

  The :class:`snapshots`5 describing the verdict and categorised violations.

