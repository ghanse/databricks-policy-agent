---
sidebar_label: model
title: policy_agent.policy.model
---

Core policy data model: resource types, effects, condition trees, and policies.

Policies are immutable, declarative data. A policy pairs a *condition tree* with an
`Effect` (allow or deny) over one `ResourceType`. Condition trees are built
from a small set of frozen node types (`Comparison`, `AllOf`, `AnyOf`,
`Negation`) so evaluation is a pure walk over data with no code execution.

## ResourceType Objects

```python
class ResourceType(str, Enum)
```

A Databricks workspace object type a policy can target.

## Effect Objects

```python
class Effect(str, Enum)
```

Whether matching a policy's rule means a resource is compliant or violating.

``ALLOW`` policies are allow-lists: a resource is compliant only when its rule matches.
``DENY`` policies are deny-lists: a resource violates the policy when its rule matches.

## EnforcementLevel Objects

```python
class EnforcementLevel(str, Enum)
```

How strongly a policy is enforced, in increasing order of strictness.

``advisory`` policies only report; ``soft`` policies block a deployment gate but may be
overridden with a recorded reason; ``hard`` policies block and cannot be overridden.

#### ENFORCEMENT\_ORDER

Enforcement levels from least to most strict.

#### meets\_threshold

```python
def meets_threshold(level: EnforcementLevel,
                    threshold: EnforcementLevel) -> bool
```

Returns whether ``level`` is at least as strict as ``threshold``.

**Arguments**:

- `level` - The level to test.
- `threshold` - The minimum strictness.
  

**Returns**:

  ``True`` when ``level`` is at or above ``threshold`` in `ENFORCEMENT_ORDER`.

## PolicyStatus Objects

```python
class PolicyStatus(str, Enum)
```

Lifecycle state of a policy in the draft-review-approve workflow.

## Condition Objects

```python
class Condition()
```

Base type for every node in a policy condition tree.

## Comparison Objects

```python
@dataclass(frozen=True)
class Comparison(Condition)
```

A leaf condition comparing one resource attribute against an expected value.

**Attributes**:

- `attribute` - Name of the resource-snapshot attribute to read. Dotted paths such as
  ``tags.environment`` index into nested mappings.
- `operator` - Name of a registered operator (see `policy_agent.policy.conditions`).
- `value` - The expected value the operator compares the attribute against. Operators
  such as ``exists`` and ``absent`` ignore it.

## AllOf Objects

```python
@dataclass(frozen=True)
class AllOf(Condition)
```

A conjunction that holds only when every child condition holds.

**Attributes**:

- `conditions` - Child conditions; an empty tuple evaluates to ``True``.

## AnyOf Objects

```python
@dataclass(frozen=True)
class AnyOf(Condition)
```

A disjunction that holds when at least one child condition holds.

**Attributes**:

- `conditions` - Child conditions; an empty tuple evaluates to ``False``.

## Negation Objects

```python
@dataclass(frozen=True)
class Negation(Condition)
```

A negation that holds when its child condition does not.

**Attributes**:

- `condition` - The child condition whose truth value is inverted.

## Policy Objects

```python
@dataclass(frozen=True)
class Policy()
```

An immutable compliance policy over a single resource type.

**Attributes**:

- `name` - Unique, human-readable policy identifier (kebab-case by convention).
- `resource_type` - The workspace object type this policy is evaluated against.
- `effect` - Whether a rule match means compliant (``ALLOW``) or violating (``DENY``).
- `rule` - The condition tree evaluated against each resource snapshot.
- `description` - Free-text explanation of the policy's intent.
- `enforcement_level` - How strongly the policy is enforced (advisory/soft/hard). Governs whether
  a deployment gate reports, blocks-with-override, or hard-blocks on a violation.
- `match` - Optional selector narrowing which resources the policy applies to; when
  ``None`` the policy applies to every resource of ``resource_type``.
- `remediation` - Guidance shown to owners on how to bring a resource into compliance.
- `status` - Position of the policy in the approval lifecycle.
- `version` - Monotonic version incremented on each approved change.

#### COMMON\_RESOURCE\_ATTRIBUTES

Attributes every resource snapshot exposes, regardless of resource type.

#### RESOURCE\_ATTRIBUTES

Attributes each resource type exposes; the contract scanning must satisfy and the set
policy validation checks attribute names against.

#### base\_attribute

```python
def base_attribute(attribute: str) -> str
```

Returns the top-level attribute name from a possibly dotted attribute path.

**Arguments**:

- `attribute` - An attribute name such as ``tags`` or a dotted path such as
  ``tags.environment``.
  

**Returns**:

  The portion of ``attribute`` before the first dot.

#### referenced\_attributes

```python
def referenced_attributes(policy: Policy) -> frozenset[str]
```

Returns the base attribute names a policy reads across its rule and match trees.

Lets a scanner fetch only the data a policy actually inspects — for example, skipping an
expensive expansion when no active policy references an attribute derived from it.

**Arguments**:

- `policy` - The policy to inspect.
  

**Returns**:

  The set of top-level attribute names (dotted paths reduced to their base) named by
  any leaf in the policy's ``rule`` or ``match`` condition trees.

