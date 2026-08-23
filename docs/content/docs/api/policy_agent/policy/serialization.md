---
sidebar_label: serialization
title: policy_agent.policy.serialization
---

Round-trip conversion between policies and plain dictionaries.

Dictionaries are the interchange format shared by the YAML loader, the storage backends,
and the app&#x27;s JSON API. Keeping conversion in one module guarantees every surface encodes
policies identically.

#### policy\_from\_dict

```python
def policy_from_dict(data: dict[str, Any]) -> Policy
```

Build a policy from a plain dictionary (e.g. parsed YAML or a JSON request body).

**Arguments**:

- `data` - Mapping with keys ``policy``/``name``, ``resource_type``, ``effect``, and
  ``rule``, plus optional ``description``, ``severity``, ``match``,
  ``remediation``, ``status``, and ``version``.
  

**Returns**:

  The constructed :class:``3.
  

**Raises**:

- ``4 - If a required key is missing or an enum value is unrecognised.

#### policy\_to\_dict

```python
def policy_to_dict(policy: Policy) -> dict[str, Any]
```

Serialise a policy to a plain dictionary with enum values rendered as strings.

**Arguments**:

- `policy` - The policy to serialise.
  

**Returns**:

  A dictionary suitable for YAML/JSON encoding and storage.

#### condition\_from\_dict

```python
def condition_from_dict(node: dict[str, Any]) -> Condition
```

Parse a condition tree from its dictionary form.

**Arguments**:

- `node` - A mapping shaped as one of ``{&quot;all&quot;: [...]}``, ``{&quot;any&quot;: [...]}``,
- ```{"not"` - {...}}``, or a leaf ``{&quot;attribute&quot;: ..., &quot;operator&quot;: ..., &quot;value&quot;: ...}``.
  

**Returns**:

  The parsed condition node.
  

**Raises**:

- ``0 - If the node shape is not recognised or a leaf omits keys.

#### condition\_to\_dict

```python
def condition_to_dict(condition: Condition) -> dict[str, Any]
```

Serialise a condition tree to its dictionary form.

**Arguments**:

- `condition` - The condition node to serialise.
  

**Returns**:

  The dictionary representation of the condition tree.
  

**Raises**:

- `InvalidPolicyError` - If the condition is an unsupported node type.

