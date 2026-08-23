"""Role model and role resolution for the approval workflow.

Roles are granted to workspace groups; a caller's effective roles are the union of the roles
mapped to every group they belong to. The permission predicates below are the single source
of truth for which role a workflow transition requires.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from enum import Enum


class Role(str, Enum):
    """A privilege level in the policy approval workflow."""

    ADMIN = "admin"
    POLICY_AUTHOR = "policy_author"
    POLICY_APPROVER = "policy_approver"
    SCAN_RUNNER = "scan_runner"
    VIEWER = "viewer"


def resolve_roles(
    group_names: Iterable[str], role_mappings: Mapping[str, Iterable[Role]]
) -> set[Role]:
    """Resolve the effective roles for a caller from their group memberships.

    Args:
        group_names: The workspace groups the caller belongs to.
        role_mappings: Mapping from group name to the roles granted to that group.

    Returns:
        The union of roles granted by the caller's groups.
    """
    resolved: set[Role] = set()
    for group_name in group_names:
        resolved.update(role_mappings.get(group_name, ()))
    return resolved


def can_author(roles: Collection[Role]) -> bool:
    """Whether the roles permit drafting and submitting policies.

    Args:
        roles: The caller's effective roles.

    Returns:
        ``True`` if authoring is permitted.
    """
    return _any_of(roles, Role.POLICY_AUTHOR, Role.ADMIN)


def can_approve(roles: Collection[Role]) -> bool:
    """Whether the roles permit approving or rejecting policies.

    Args:
        roles: The caller's effective roles.

    Returns:
        ``True`` if approval is permitted.
    """
    return _any_of(roles, Role.POLICY_APPROVER, Role.ADMIN)


def can_run_scans(roles: Collection[Role]) -> bool:
    """Whether the roles permit running scans.

    Args:
        roles: The caller's effective roles.

    Returns:
        ``True`` if running scans is permitted.
    """
    return _any_of(roles, Role.SCAN_RUNNER, Role.ADMIN)


def can_administer(roles: Collection[Role]) -> bool:
    """Whether the roles permit administrative actions such as archiving.

    Args:
        roles: The caller's effective roles.

    Returns:
        ``True`` if administration is permitted.
    """
    return Role.ADMIN in roles


def _any_of(roles: Collection[Role], *allowed: Role) -> bool:
    return any(role in roles for role in allowed)
