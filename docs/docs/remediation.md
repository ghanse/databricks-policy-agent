---
sidebar_position: 8
---

# Remediation cycle

Violations are tracked as **remediation items** that an owner drives to resolution. Each item
is keyed by the `(policy, resource type, resource id)` it concerns.

## Statuses

- `open` — a newly detected violation.
- `in_progress` — someone is working on it.
- `resolved` — the violation has been fixed (manually or auto-resolved on re-scan).
- `waived` — the violation is knowingly accepted.

## Reconciliation

When a scan runs, `reconcile` diffs the currently-open items against the fresh violations:

- New violations open new items.
- Open items whose violation no longer appears are **auto-resolved**.
- Resolved and waived items are preserved.

```python
from datetime import datetime, timezone
from policy_agent.remediation import reconcile

updated = reconcile(existing_items, scan_result.violations, scan_result.scan_id,
                    datetime.now(timezone.utc))
```

The provisioned scan jobs run this reconciliation automatically after each scan, and the app
exposes manual transitions (advance, resolve, waive, assign) on the Remediations tab.
