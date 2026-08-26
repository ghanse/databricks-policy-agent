---
sidebar_label: sources
title: policy_agent.enforce.sources
---

Maps a resolved bundle configuration into evaluable resource snapshots.

Each declared resource under ``resources.<group>.<key>`` is normalised into the same
`ResourceSnapshot` shape produced by a live scan, so the enforcement gate reuses the
existing evaluation engine unchanged. Only *declarable* attributes are populated; attributes
known only at runtime (for example ``created_time``) are ``None``.

#### snapshot\_bundle

```python
def snapshot_bundle(config: dict[str, Any]) -> list[ResourceSnapshot]
```

Builds resource snapshots from a resolved bundle configuration.

**Arguments**:

- `config` - A resolved bundle configuration (see `load_bundle_config`).
  

**Returns**:

  One snapshot per supported declared resource, in resource-group order.

