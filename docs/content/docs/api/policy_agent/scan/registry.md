---
sidebar_label: registry
title: policy_agent.scan.registry
---

Registry mapping each resource type to the function that fetches its snapshots.

Adding support for a new resource type is a one-line change here plus a ``scan_*`` function
in `policy_agent.scan.resources` and an attribute set in
`policy_agent.policy.model.RESOURCE_ATTRIBUTES`.

#### RESOURCE\_SCANNERS

The resource types the framework can scan, keyed to their fetch functions.

#### supported\_resource\_types

```python
def supported_resource_types() -> tuple[ResourceType, ...]
```

Returns every resource type that has a registered scanner.

**Returns**:

  The supported resource types, in registration order.

#### scanner\_for

```python
def scanner_for(resource_type: ResourceType) -> ResourceScanner
```

Returns the scanner function registered for a resource type.

**Arguments**:

- `resource_type` - The resource type to look up.
  

**Returns**:

  The function that fetches snapshots for the resource type.
  

**Raises**:

- `UnsupportedResourceException` - If no scanner is registered for the resource type.

