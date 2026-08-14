"""Policy approval workflow: roles, permissions, and the transition state machine.

from policy_agent.approval import Role, submit_for_review, approve, reject, archive
"""

from policy_agent.approval.roles import (
    Role,
    can_administer,
    can_approve,
    can_author,
    can_run_scans,
    resolve_roles,
)
from policy_agent.approval.workflow import (
    ApprovalEvent,
    approve,
    archive,
    reject,
    submit_for_review,
)

__all__ = [
    "ApprovalEvent",
    "Role",
    "approve",
    "archive",
    "can_administer",
    "can_approve",
    "can_author",
    "can_run_scans",
    "reject",
    "resolve_roles",
    "submit_for_review",
]
