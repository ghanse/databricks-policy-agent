---
sidebar_label: serialization
title: policy_agent.policy.serialization
---

Round-trip conversion between policies and plain dictionaries.

Dictionaries are the interchange format shared by the YAML loader, the storage backends,
and the app's JSON API. Keeping conversion in one module guarantees every surface encodes
policies identically.

#### policy\_from\_dict

```python
def policy_from_dict(data: dict[str, Any]) -> Policy
```

Builds a policy from a plain dictionary (e.g. parsed YAML or a JSON request body).

**Arguments**:

- `data` - Mapping with keys ``policy``/``name``, ``resource_type``, ``effect``, and
  ``rule``, plus optional ``description``, ``enforcement_level``, ``match``,
  ``remediation``, ``status``, and ``version``.
  

**Returns**:

  The constructed `Policy`.
  

**Raises**:

- `InvalidPolicyError` - If a required key is missing or an enum value is unrecognised.
- `UnsupportedResourceException` - If ``resource_type`` names a type the agent does not support.

#### policy\_to\_dict

```python
def policy_to_dict(policy: Policy) -> dict[str, Any]
```

Serialises a policy to a plain dictionary with enum values rendered as strings.

**Arguments**:

- `policy` - The policy to serialise.
  

**Returns**:

  A dictionary suitable for YAML/JSON encoding and storage.

#### condition\_from\_dict

```python
def condition_from_dict(node: dict[str, Any]) -> Condition
```

Parses a condition tree from its dictionary form.

**Arguments**:

- `node` - A mapping shaped as one of ``{"all": [...]}``, ``{"any": [...]}``,
- ```{"not"` - {...}}``, or a leaf ``{"attribute": ..., "operator": ..., "value": ...}``.
  

**Returns**:

  The parsed condition node.
  

**Raises**:

- `InvalidPolicyError` - If the node shape is not recognised or a leaf omits keys.

#### condition\_to\_dict

```python
def condition_to_dict(condition: Condition) -> dict[str, Any]
```

Serialises a condition tree to its dictionary form.

**Arguments**:

- `condition` - The condition node to serialise.
  

**Returns**:

  The dictionary representation of the condition tree.
  

**Raises**:

- `InvalidPolicyError` - If the condition is an unsupported node type.

