---
sidebar_label: cycle
title: policy_agent.remediation.cycle
---

Pure functions that drive the remediation cycle.

A violation is tracked by the ``(policy, resource type, resource id)`` it concerns.
``reconcile`` diffs the currently-open items against a fresh scan's violations: new
violations open items, and open items whose violation has cleared are auto-resolved. The
manual transitions (`advance`, `resolve`, `waive`, `assign`) let an
owner move an item by hand.

#### reconcile

```python
def reconcile(existing_items: Iterable[RemediationItem],
              violations: Iterable[Finding], scan_id: str,
              now: datetime) -> list[RemediationItem]
```

Reconcile open remediation items against a fresh scan's violations.

**Arguments**:

- `existing_items` - Remediation items already tracked from earlier scans.
- `violations` - The violating findings from the latest scan.
- `scan_id` - Identifier of the latest scan.
- `now` - Timestamp applied to any status change.
  

**Returns**:

  The updated set of remediation items: unchanged resolved/waived items, auto-resolved
  items whose violation has cleared, still-open items, and newly opened items.

#### open\_items\_from\_findings

```python
def open_items_from_findings(violations: Iterable[Finding], scan_id: str,
                             now: datetime) -> list[RemediationItem]
```

Open a fresh remediation item for every violation.

**Arguments**:

- `violations` - The violating findings.
- `scan_id` - Identifier of the scan that produced them.
- `now` - Timestamp applied to the opened items.
  

**Returns**:

  One open remediation item per violation.

#### advance

```python
def advance(item: RemediationItem,
            now: datetime,
            note: str = "") -> RemediationItem
```

Mark an item as in progress.

**Arguments**:

- `item` - The item to advance.
- `now` - Timestamp of the change.
- `note` - Optional note recorded on the item.
  

**Returns**:

  The updated item.

#### resolve

```python
def resolve(item: RemediationItem,
            now: datetime,
            note: str = "") -> RemediationItem
```

Mark an item as resolved.

**Arguments**:

- `item` - The item to resolve.
- `now` - Timestamp of the change.
- `note` - Optional note recorded on the item.
  

**Returns**:

  The updated item.

#### waive

```python
def waive(item: RemediationItem,
          now: datetime,
          note: str = "") -> RemediationItem
```

Waive an item, accepting the violation without changing the resource.

**Arguments**:

- `item` - The item to waive.
- `now` - Timestamp of the change.
- `note` - Optional justification recorded on the item.
  

**Returns**:

  The updated item.

#### assign

```python
def assign(item: RemediationItem, assignee: str,
           now: datetime) -> RemediationItem
```

Assign an item to a principal responsible for resolving it.

**Arguments**:

- `item` - The item to assign.
- `assignee` - The principal to assign.
- `now` - Timestamp of the change.
  

**Returns**:

  The updated item.

