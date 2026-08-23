---
sidebar_label: workflow
title: policy_agent.approval.workflow
---

The policy approval state machine.

Transitions are pure functions: each takes a policy plus the acting principal&#x27;s roles and
returns a new policy and an audit :class:`ApprovalEvent`. Illegal transitions raise
:class:`WorkflowError`; insufficient privilege raises :class:`AuthorizationError`. Only an
``APPROVED`` policy is eligible to be run by scans.

## ApprovalEvent Objects

```python
@dataclass(frozen=True)
class ApprovalEvent()
```

An immutable audit record of one approval-workflow transition.

**Attributes**:

- `event_id` - Unique identifier for the event.
- `policy_name` - Name of the policy that transitioned.
- `from_status` - Status before the transition.
- `to_status` - Status after the transition.
- `actor` - Principal who performed the transition.
- `note` - Optional free-text justification.
- `created_at` - When the transition occurred.

#### submit\_for\_review

```python
def submit_for_review(policy: Policy,
                      actor: str,
                      roles: Collection[Role],
                      note: str = "") -> tuple[Policy, ApprovalEvent]
```

Move a draft or rejected policy into review.

**Arguments**:

- `policy` - The policy to submit.
- `actor` - The submitting principal.
- `roles` - The actor&#x27;s effective roles.
- `note` - Optional justification recorded on the event.
  

**Returns**:

  The updated policy and the recorded approval event.
  

**Raises**:

- `AuthorizationError` - If the actor cannot author policies.
- `WorkflowError` - If the policy is not in ``draft`` or ``rejected`` status.

#### approve

```python
def approve(policy: Policy,
            actor: str,
            roles: Collection[Role],
            note: str = "",
            author: str | None = None) -> tuple[Policy, ApprovalEvent]
```

Approve a policy under review, incrementing its version.

**Arguments**:

- `policy` - The policy to approve.
- `actor` - The approving principal.
- `roles` - The actor&#x27;s effective roles.
- `note` - Optional justification recorded on the event.
- `author` - When provided, the approver must differ from the author (separation of
  duties); approving one&#x27;s own submission raises.
  

**Returns**:

  The approved policy (with an incremented version) and the recorded event.
  

**Raises**:

- `AuthorizationError` - If the actor cannot approve, or is the policy&#x27;s author.
- `WorkflowError` - If the policy is not in ``in_review`` status.

#### reject

```python
def reject(policy: Policy,
           actor: str,
           roles: Collection[Role],
           note: str = "") -> tuple[Policy, ApprovalEvent]
```

Reject a policy under review, returning it to the author.

**Arguments**:

- `policy` - The policy to reject.
- `actor` - The rejecting principal.
- `roles` - The actor&#x27;s effective roles.
- `note` - Optional justification recorded on the event.
  

**Returns**:

  The rejected policy and the recorded event.
  

**Raises**:

- `AuthorizationError` - If the actor cannot approve policies.
- `WorkflowError` - If the policy is not in ``in_review`` status.

#### archive

```python
def archive(policy: Policy,
            actor: str,
            roles: Collection[Role],
            note: str = "") -> tuple[Policy, ApprovalEvent]
```

Archive a policy from any status, retiring it from scans.

**Arguments**:

- `policy` - The policy to archive.
- `actor` - The archiving principal.
- `roles` - The actor&#x27;s effective roles.
- `note` - Optional justification recorded on the event.
  

**Returns**:

  The archived policy and the recorded event.
  

**Raises**:

- `AuthorizationError` - If the actor is not an administrator.

