"""Shared entity lookups that raise the appropriate HTTP error when absent."""

from __future__ import annotations

from fastapi import HTTPException, status
from policy_agent.config import PolicyAgentConfig
from policy_agent.policy.model import Policy
from policy_agent.remediation.model import RemediationItem
from policy_agent.storage.backend import SqlExecutor, load_policies, read_remediations


def find_policy(executor: SqlExecutor, config: PolicyAgentConfig, name: str) -> Policy:
    """Returns a policy by name or raises ``404``.

    Args:
        executor: The storage executor.
        config: The runtime configuration.
        name: The policy name.

    Returns:
        The matching policy.

    Raises:
        HTTPException: ``404`` if no policy has the given name.
    """
    for policy in load_policies(executor, config.storage):
        if policy.name == name:
            return policy
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown policy {name!r}.")


def find_remediation(
    executor: SqlExecutor, config: PolicyAgentConfig, remediation_id: str
) -> RemediationItem:
    """Returns a remediation item by id or raises ``404``.

    Args:
        executor: The storage executor.
        config: The runtime configuration.
        remediation_id: The remediation item id.

    Returns:
        The matching remediation item.

    Raises:
        HTTPException: ``404`` if no remediation item has the given id.
    """
    for item in read_remediations(executor, config.storage):
        if item.remediation_id == remediation_id:
            return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Unknown remediation {remediation_id!r}.",
    )
