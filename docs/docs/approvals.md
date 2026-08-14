---
sidebar_position: 7
---

# Approvals & roles

Policy changes are gated behind a review workflow so that drafting, approving, and running
are separated across privilege levels.

## Roles

| Role | Grants |
| --- | --- |
| `admin` | everything, including archiving policies and managing role mappings |
| `policy_author` | draft and submit policies for review |
| `policy_approver` | approve or reject policies under review |
| `scan_runner` | run scans |
| `viewer` | read-only access |

Roles are granted to workspace groups; a caller's effective roles are the union of the roles
mapped to their groups. As a bootstrap convenience, when no role mappings exist yet every
caller is treated as an administrator so the first mappings can be configured through the app.

## Lifecycle

```
draft ──submit──▶ in_review ──approve──▶ approved ──archive──▶ archived
  ▲                   │
  └──────submit───── rejected ◀──reject──┘
```

- **submit** (author): `draft`/`rejected` → `in_review`.
- **approve** (approver, and — when enforced — not the author): `in_review` → `approved`,
  incrementing the policy version.
- **reject** (approver): `in_review` → `rejected`.
- **archive** (admin): any status → `archived`.

Every transition writes an immutable `ApprovalEvent` audit record. Only **approved** policies
are evaluated by scans.

```python
from policy_agent.approval import Role, submit_for_review, approve

in_review, submit_event = submit_for_review(policy, "alice@example.com", {Role.POLICY_AUTHOR})
approved, approve_event = approve(in_review, "bob@example.com", {Role.POLICY_APPROVER})
```
