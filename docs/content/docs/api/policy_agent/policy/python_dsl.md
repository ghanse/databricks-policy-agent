---
sidebar_label: python_dsl
title: policy_agent.policy.python_dsl
---

Functional constructors for declaring policies and condition trees in Python.

These helpers are thin, keyword-friendly wrappers over the frozen model types. They coerce
string inputs (resource type, enforcement) into their enums so callers can write policies
without importing every enum member.

**Example**:

  &gt;&gt;&gt; from policy_agent.policy import deny, any_of, leaf, ResourceType
  &gt;&gt;&gt; policy = deny(
  ...     name=&quot;only-service-principals-own-compute&quot;,
  ...     resource_type=ResourceType.CLUSTER,
  ...     rule=any_of(leaf(&quot;owner_type&quot;, &quot;not_equals&quot;, &quot;service_principal&quot;)),
  ... )

#### deny

```python
def deny(name: str,
         resource_type: ResourceType | str,
         rule: Condition,
         *,
         description: str = "",
         enforcement: EnforcementLevel | str = EnforcementLevel.ADVISORY,
         match: Condition | None = None,
         remediation: str = "",
         status: PolicyStatus | str = PolicyStatus.DRAFT,
         version: int = 1) -> Policy
```

Build a deny-list policy: resources whose rule matches are violations.

**Arguments**:

- `name` - Unique policy identifier.
- `resource_type` - Target resource type, as a :class:`ResourceType` or its string value.
- `rule` - Condition tree whose match marks a resource as violating.
- `description` - Free-text explanation of intent.
- `enforcement` - How strongly the policy is enforced; an EnforcementLevel or its string value.
- `match` - Optional selector limiting which resources the policy applies to.
- `remediation` - Guidance for bringing a resource into compliance.
- `status` - Initial approval-lifecycle status.
- `version` - Initial version number.
  

**Returns**:

  A :class:`resource_type`0 with :attr:`resource_type`1.

#### allow

```python
def allow(name: str,
          resource_type: ResourceType | str,
          rule: Condition,
          *,
          description: str = "",
          enforcement: EnforcementLevel | str = EnforcementLevel.ADVISORY,
          match: Condition | None = None,
          remediation: str = "",
          status: PolicyStatus | str = PolicyStatus.DRAFT,
          version: int = 1) -> Policy
```

Build an allow-list policy: resources whose rule does not match are violations.

**Arguments**:

- `name` - Unique policy identifier.
- `resource_type` - Target resource type, as a :class:`ResourceType` or its string value.
- `rule` - Condition tree a compliant resource must match.
- `description` - Free-text explanation of intent.
- `enforcement` - How strongly the policy is enforced; an EnforcementLevel or its string value.
- `match` - Optional selector limiting which resources the policy applies to.
- `remediation` - Guidance for bringing a resource into compliance.
- `status` - Initial approval-lifecycle status.
- `version` - Initial version number.
  

**Returns**:

  A :class:`resource_type`0 with :attr:`resource_type`1.

#### policy

```python
def policy(name: str,
           resource_type: ResourceType | str,
           effect: Effect | str,
           rule: Condition,
           *,
           description: str = "",
           enforcement: EnforcementLevel | str = EnforcementLevel.ADVISORY,
           match: Condition | None = None,
           remediation: str = "",
           status: PolicyStatus | str = PolicyStatus.DRAFT,
           version: int = 1) -> Policy
```

Build a policy with an explicit effect, coercing string enum inputs.

**Arguments**:

- `name` - Unique policy identifier.
- `resource_type` - Target resource type, as a :class:`ResourceType` or its string value.
- `effect` - Whether a rule match means compliant (``allow``) or violating (``deny``).
- `rule` - The condition tree evaluated against each resource.
- `description` - Free-text explanation of intent.
- `resource_type`0 - How strongly the policy is enforced; an EnforcementLevel or its string value.
- `resource_type`1 - Optional selector limiting which resources the policy applies to.
- `resource_type`2 - Guidance for bringing a resource into compliance.
- `resource_type`3 - Initial approval-lifecycle status.
- `resource_type`4 - Initial version number.
  

**Returns**:

  The constructed :class:`resource_type`5.

#### leaf

```python
def leaf(attribute: str, operator: str, value: object = None) -> Comparison
```

Build a leaf comparison condition.

**Arguments**:

- `attribute` - Resource attribute name or dotted path (e.g. ``tags.environment``).
- `operator` - Registered operator name (e.g. ``equals``, ``matches_regex``).
- `value` - Expected value the operator compares against; unused by operators such as
  ``exists`` and ``absent``.
  

**Returns**:

  A :class:``3 node.

#### all\_of

```python
def all_of(*conditions: Condition) -> AllOf
```

Build a conjunction that holds only when every child condition holds.

**Arguments**:

- `*conditions` - Child conditions.
  

**Returns**:

  An :class:`AllOf` node.

#### any\_of

```python
def any_of(*conditions: Condition) -> AnyOf
```

Build a disjunction that holds when at least one child condition holds.

**Arguments**:

- `*conditions` - Child conditions.
  

**Returns**:

  An :class:`AnyOf` node.

#### not\_

```python
def not_(condition: Condition) -> Negation
```

Build a negation that holds when its child condition does not.

**Arguments**:

- `condition` - The condition to negate.
  

**Returns**:

  A :class:`Negation` node.

