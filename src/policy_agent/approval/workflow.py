"""The policy approval state machine.

Transitions are pure functions: each takes a policy plus the acting principal's roles and
returns a new policy and an audit :class:`ApprovalEvent`. Illegal transitions raise
:class:`WorkflowError`; insufficient privilege raises :class:`AuthorizationError`. Only an
``APPROVED`` policy is eligible to be run by scans.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from policy_agent.approval.roles import Role, can_administer, can_approve, can_author
from policy_agent.errors import AuthorizationError, WorkflowError
from policy_agent.policy.model import Policy, PolicyStatus


@dataclass(frozen=True)
class ApprovalEvent:
    """An immutable audit record of one approval-workflow transition.

    Attributes:
        event_id: Unique identifier for the event.
        policy_name: Name of the policy that transitioned.
        from_status: Status before the transition.
        to_status: Status after the transition.
        actor: Principal who performed the transition.
        note: Optional free-text justification.
        created_at: When the transition occurred.
    """

    event_id: str
    policy_name: str
    from_status: PolicyStatus
    to_status: PolicyStatus
    actor: str
    note: str
    created_at: datetime


def submit_for_review(
    policy: Policy, actor: str, roles: Collection[Role], note: str = ""
) -> tuple[Policy, ApprovalEvent]:
    """Move a draft or rejected policy into review.

    Args:
        policy: The policy to submit.
        actor: The submitting principal.
        roles: The actor's effective roles.
        note: Optional justification recorded on the event.

    Returns:
        The updated policy and the recorded approval event.

    Raises:
        AuthorizationError: If the actor cannot author policies.
        WorkflowError: If the policy is not in ``draft`` or ``rejected`` status.
    """
    _require(can_author(roles), "author policies")
    _require_status(policy, {PolicyStatus.DRAFT, PolicyStatus.REJECTED})
    return _transition(policy, PolicyStatus.IN_REVIEW, actor, note)


def approve(
    policy: Policy,
    actor: str,
    roles: Collection[Role],
    note: str = "",
    author: str | None = None,
) -> tuple[Policy, ApprovalEvent]:
    """Approve a policy under review, incrementing its version.

    Args:
        policy: The policy to approve.
        actor: The approving principal.
        roles: The actor's effective roles.
        note: Optional justification recorded on the event.
        author: When provided, the approver must differ from the author (separation of
            duties); approving one's own submission raises.

    Returns:
        The approved policy (with an incremented version) and the recorded event.

    Raises:
        AuthorizationError: If the actor cannot approve, or is the policy's author.
        WorkflowError: If the policy is not in ``in_review`` status.
    """
    _require(can_approve(roles), "approve policies")
    if author is not None and author == actor:
        raise AuthorizationError("An approver may not approve their own policy submission.")
    _require_status(policy, {PolicyStatus.IN_REVIEW})
    approved = replace(policy, version=policy.version + 1)
    return _transition(approved, PolicyStatus.APPROVED, actor, note)


def reject(
    policy: Policy, actor: str, roles: Collection[Role], note: str = ""
) -> tuple[Policy, ApprovalEvent]:
    """Reject a policy under review, returning it to the author.

    Args:
        policy: The policy to reject.
        actor: The rejecting principal.
        roles: The actor's effective roles.
        note: Optional justification recorded on the event.

    Returns:
        The rejected policy and the recorded event.

    Raises:
        AuthorizationError: If the actor cannot approve policies.
        WorkflowError: If the policy is not in ``in_review`` status.
    """
    _require(can_approve(roles), "reject policies")
    _require_status(policy, {PolicyStatus.IN_REVIEW})
    return _transition(policy, PolicyStatus.REJECTED, actor, note)


def archive(
    policy: Policy, actor: str, roles: Collection[Role], note: str = ""
) -> tuple[Policy, ApprovalEvent]:
    """Archive a policy from any status, retiring it from scans.

    Args:
        policy: The policy to archive.
        actor: The archiving principal.
        roles: The actor's effective roles.
        note: Optional justification recorded on the event.

    Returns:
        The archived policy and the recorded event.

    Raises:
        AuthorizationError: If the actor is not an administrator.
    """
    _require(can_administer(roles), "archive policies")
    return _transition(policy, PolicyStatus.ARCHIVED, actor, note)


def _transition(
    policy: Policy, to_status: PolicyStatus, actor: str, note: str
) -> tuple[Policy, ApprovalEvent]:
    event = ApprovalEvent(
        event_id=uuid.uuid4().hex,
        policy_name=policy.name,
        from_status=policy.status,
        to_status=to_status,
        actor=actor,
        note=note,
        created_at=datetime.now(UTC),
    )
    return replace(policy, status=to_status), event


def _require(condition: bool, action: str) -> None:
    if not condition:
        raise AuthorizationError(f"Caller is not permitted to {action}.")


def _require_status(policy: Policy, allowed: set[PolicyStatus]) -> None:
    if policy.status not in allowed:
        allowed_values = sorted(status.value for status in allowed)
        raise WorkflowError(
            f"Policy {policy.name!r} is {policy.status.value!r}; expected one of {allowed_values}."
        )
