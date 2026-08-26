---
sidebar_label: yaml_loader
title: policy_agent.policy.yaml_loader
---

Loads and dump policies in the OPA-style YAML authoring format.

A YAML source may hold a single policy mapping, a top-level list of policies, or several
documents separated by ``---``. Loaded policies are validated before being returned so a
malformed policy fails fast at load time.

#### load\_policies\_from\_yaml

```python
def load_policies_from_yaml(source: str | Path) -> list[Policy]
```

Loads and validate every policy from a YAML string or file path.

**Arguments**:

- `source` - Either YAML text or a path to a ``.yml``/``.yaml`` file.
  

**Returns**:

  The validated policies, in document order.
  

**Raises**:

- `InvalidPolicyError` - If the YAML is malformed or any policy fails validation.

#### dump\_policies\_to\_yaml

```python
def dump_policies_to_yaml(policies: list[Policy]) -> str
```

Serialises policies to a single multi-document YAML string.

**Arguments**:

- `policies` - The policies to serialise.
  

**Returns**:

  YAML text with one document per policy, in the given order.

