"""Data model for the remediation cycle that tracks violations to resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from policy_agent.policy.model import EnforcementLevel, ResourceType


class RemediationStatus(str, Enum):
    """Lifecycle state of a remediation item."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WAIVED = "waived"


OPEN_STATUSES: frozenset[RemediationStatus] = frozenset(
    {RemediationStatus.OPEN, RemediationStatus.IN_PROGRESS}
)
"""Statuses that represent an unresolved item still requiring attention."""


class RemediationEventType(str, Enum):
    """The kind of activity captured on a remediation item's audit trail."""

    OPENED = "opened"
    ASSIGNED = "assigned"
    ADVANCED = "advanced"
    RESOLVED = "resolved"
    WAIVED = "waived"
    COMMENTED = "commented"
    AUTO_RESOLVED = "auto_resolved"
    AGENT_PROPOSED = "agent_proposed"
    AGENT_ACCEPTED = "agent_accepted"
    AGENT_REJECTED = "agent_rejected"


@dataclass(frozen=True)
class RemediationEvent:
    """An immutable audit record of one activity on a remediation item.

    Every status change, comment, assignment, and Genie Code interaction appends one of
    these so the item's full history can be reconstructed. Events are never mutated or
    deleted.

    Attributes:
        event_id: Unique identifier for the event.
        remediation_id: The remediation item the event belongs to.
        event_type: The kind of activity recorded.
        actor: Principal (or process) that performed the activity.
        note: Free-text comment or justification, if any.
        from_status: Status before the change, when the event changed status.
        to_status: Status after the change, when the event changed status.
        payload: Optional serialized detail (for example a Genie Code proposal), as JSON.
        created_at: When the activity occurred.
    """

    event_id: str
    remediation_id: str
    event_type: RemediationEventType
    actor: str
    note: str = ""
    from_status: RemediationStatus | None = None
    to_status: RemediationStatus | None = None
    payload: str = ""
    created_at: datetime | None = None


@dataclass(frozen=True)
class RemediationItem:
    """A tracked violation moving through the remediation cycle.

    Attributes:
        remediation_id: Unique identifier for the item.
        policy_name: Name of the violated policy.
        resource_type: Type of the violating resource.
        resource_id: Identifier of the violating resource.
        resource_name: Display name of the violating resource.
        enforcement_level: Enforcement level inherited from the violated policy.
        status: Current lifecycle status.
        scan_id: Identifier of the scan that opened the item.
        opened_at: When the item was first opened.
        updated_at: When the item last changed status.
        assignee: Principal responsible for resolving the item, if assigned.
        note: Free-text note recorded on the most recent transition.
    """

    remediation_id: str
    policy_name: str
    resource_type: ResourceType
    resource_id: str
    resource_name: str
    enforcement_level: EnforcementLevel
    status: RemediationStatus
    scan_id: str
    opened_at: datetime
    updated_at: datetime
    assignee: str | None = None
    note: str = ""

    @property
    def is_open(self) -> bool:
        """Whether this item still requires attention."""
        return self.status in OPEN_STATUSES
