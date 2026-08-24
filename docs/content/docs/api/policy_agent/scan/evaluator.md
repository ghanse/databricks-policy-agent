---
sidebar_label: evaluator
title: policy_agent.scan.evaluator
---

Pure evaluation of a single policy against a single resource snapshot.

#### evaluate\_resource

```python
def evaluate_resource(policy: Policy,
                      snapshot: ResourceSnapshot) -> Finding | None
```

Evaluate one policy against one resource snapshot.

A policy that targets a different resource type, or whose optional ``match`` selector
excludes the resource, does not apply and yields no finding.

**Arguments**:

- `policy` - The policy to evaluate.
- `snapshot` - The resource snapshot to evaluate against.
  

**Returns**:

  A `Finding` describing the outcome, or ``None`` when the policy does not
  apply to this resource.

