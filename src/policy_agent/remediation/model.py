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


@dataclass(frozen=True)
class RemediationItem:
    """A tracked violation moving through the remediation cycle.

    Attributes:
        remediation_id: Unique identifier for the item.
        policy_name: Name of the violated policy.
        resource_type: Type of the violating resource.
        resource_id: Identifier of the violating resource.
        resource_name: Display name of the violating resource.
        enforcement: Enforcement level inherited from the violated policy.
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
    enforcement: EnforcementLevel
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
