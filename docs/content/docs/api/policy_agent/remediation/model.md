---
sidebar_label: model
title: policy_agent.remediation.model
---

Data model for the remediation cycle that tracks violations to resolution.

## RemediationStatus Objects

```python
class RemediationStatus(str, Enum)
```

Lifecycle state of a remediation item.

#### OPEN\_STATUSES

Statuses that represent an unresolved item still requiring attention.

## RemediationItem Objects

```python
@dataclass(frozen=True)
class RemediationItem()
```

A tracked violation moving through the remediation cycle.

**Attributes**:

- `remediation_id` - Unique identifier for the item.
- `policy_name` - Name of the violated policy.
- `resource_type` - Type of the violating resource.
- `resource_id` - Identifier of the violating resource.
- `resource_name` - Display name of the violating resource.
- `enforcement` - Enforcement level inherited from the violated policy.
- `status` - Current lifecycle status.
- `scan_id` - Identifier of the scan that opened the item.
- `opened_at` - When the item was first opened.
- `updated_at` - When the item last changed status.
- `assignee` - Principal responsible for resolving the item, if assigned.
- `note` - Free-text note recorded on the most recent transition.

#### is\_open

```python
@property
def is_open() -> bool
```

Whether this item still requires attention.

