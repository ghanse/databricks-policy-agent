---
sidebar_label: registry
title: policy_agent.scan.registry
---

Registry mapping each resource type to the function that fetches its snapshots.

Adding support for a new resource type is a one-line change here plus a ``scan_*`` function
in `policy_agent.scan.resources` and an attribute set in
`policy_agent.policy.model.RESOURCE_ATTRIBUTES`.

#### RESOURCE\_SCANNERS

The resource types the framework can scan, keyed to their fetch functions. Some supported
resource types (e.g. quality monitors) have no list API and so are enforce-only, not scannable.

#### supported\_resource\_types

```python
def supported_resource_types() -> tuple[ResourceType, ...]
```

Return every resource type that has a registered scanner.

**Returns**:

  The supported resource types, in registration order.

#### is\_scannable

```python
def is_scannable(resource_type: ResourceType) -> bool
```

Return whether a resource type can be live-scanned.

Enforce-only types (those without a workspace list API, such as quality monitors) can still
be evaluated from a bundle by the enforcement gate, but never by a live scan.

**Arguments**:

- `resource_type` - The resource type to check.
  

**Returns**:

  ``True`` if a scanner is registered for the resource type.

#### scanner\_for

```python
def scanner_for(resource_type: ResourceType) -> ResourceScanner
```

Return the scanner function registered for a resource type.

**Arguments**:

- `resource_type` - The resource type to look up.
  

**Returns**:

  The function that fetches snapshots for the resource type.
  

**Raises**:

- `KeyError` - If no scanner is registered for the resource type.

