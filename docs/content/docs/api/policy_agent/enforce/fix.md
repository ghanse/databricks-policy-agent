---
sidebar_label: fix
title: policy_agent.enforce.fix
---

Suggested remediations for violating declared resources.

Because the gate evaluates the *resolved* bundle (variables and target overrides already
applied), it cannot always map a change back to the exact line of templated source. So v1
mutation surfaces the policy&#x27;s authored remediation guidance per violating resource — a
suggestion an author applies — rather than silently rewriting ``databricks.yml``.

#### suggest\_fixes

```python
def suggest_fixes(
        violations: Iterable[Finding],
        policies_by_name: Mapping[str, Policy]) -> tuple[FixSuggestion, ...]
```

Build a remediation suggestion for each violation.

**Arguments**:

- `violations` - The violating findings.
- `policies_by_name` - Policies keyed by name, used to source remediation guidance.
  

**Returns**:

  One :class:`FixSuggestion` per violation, in order.

