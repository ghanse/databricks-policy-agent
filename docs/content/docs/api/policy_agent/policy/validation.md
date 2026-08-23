---
sidebar_label: validation
title: policy_agent.policy.validation
---

Structural validation of policies and condition trees.

Validation guarantees a policy can be evaluated safely: every leaf names a registered
operator and an attribute the target resource type actually exposes. This is what makes the
declarative model safe — an unrecognised operator or attribute is rejected at author time
rather than silently ignored during a scan.

#### validate\_policy

```python
def validate_policy(policy: Policy) -> None
```

Validate a policy&#x27;s identity and both of its condition trees.

**Arguments**:

- `policy` - The policy to validate.
  

**Raises**:

- `InvalidPolicyError` - If the name is empty or an attribute is invalid for the type.
- `UnknownConditionError` - If any leaf references an unregistered operator.

#### validate\_condition

```python
def validate_condition(condition: Condition,
                       resource_type: ResourceType) -> None
```

Recursively validate a condition tree against a resource type&#x27;s attributes.

**Arguments**:

- `condition` - The condition tree to validate.
- `resource_type` - The resource type whose attribute set leaves are checked against.
  

**Raises**:

- `InvalidPolicyError` - If a leaf names an attribute the resource type does not expose.
- `UnknownConditionError` - If a leaf references an unregistered operator.

