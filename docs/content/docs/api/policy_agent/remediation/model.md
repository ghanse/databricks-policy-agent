---
sidebar_label: model
title: policy_agent.remediation.model
---

Data model for the remediation cycle that tracks violations to resolution.

## RemediationStatus Objects

```python
class RemediationStatus(StrEnum)
```

Lifecycle state of a remediation item.

#### OPEN\_STATUSES

Statuses that represent an unresolved item still requiring attention.

## RemediationEventType Objects

```python
class RemediationEventType(StrEnum)
```

The kind of activity captured on a remediation item's audit trail.

## RemediationEvent Objects

```python
@dataclass(frozen=True)
class RemediationEvent()
```

An immutable audit record of one activity on a remediation item.

Every status change, comment, assignment, and Genie Code interaction appends one of
these so the item's full history can be reconstructed. Events are never mutated or
deleted.

**Attributes**:

- `event_id` - Unique identifier for the event.
- `remediation_id` - The remediation item the event belongs to.
- `event_type` - The kind of activity recorded.
- `actor` - Principal (or process) that performed the activity.
- `note` - Free-text comment or justification, if any.
- `from_status` - Status before the change, when the event changed status.
- `to_status` - Status after the change, when the event changed status.
- `payload` - Optional serialized detail (for example a Genie Code proposal), as JSON.
- `created_at` - When the activity occurred.

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
- `enforcement_level` - Enforcement level inherited from the violated policy.
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

