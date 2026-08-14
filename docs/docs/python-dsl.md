---
sidebar_position: 4
---

# Python DSL

Policies can be declared in Python with functional constructors that mirror the YAML format.

```python
from policy_agent.policy import deny, allow, all_of, any_of, leaf, ResourceType

deny(
    name="clusters-owned-by-service-principals",
    resource_type=ResourceType.CLUSTER,
    severity="high",
    match=all_of(leaf("cluster_source", "equals", "UI")),
    rule=any_of(leaf("owner_type", "not_equals", "service_principal")),
    remediation="Recreate the cluster under an approved service principal.",
)

allow(
    name="jobs-naming-convention",
    resource_type="job",
    rule=all_of(leaf("name", "matches_regex", r"^(prod|stg|dev)_[a-z0-9_]+$")),
)
```

- `deny(...)` / `allow(...)` set the effect; `policy(...)` takes an explicit `effect`.
- `all_of(*conditions)`, `any_of(*conditions)`, `not_(condition)` build the tree.
- `leaf(attribute, operator, value=None)` builds a comparison.
- String values for `resource_type`, `effect`, and `severity` are coerced to their enums.

The constructors return immutable `Policy` objects — the same type the YAML loader
produces — so both authoring paths converge on one model. See the generated
[API reference](api/policy_agent/policy/model.md) for details.
