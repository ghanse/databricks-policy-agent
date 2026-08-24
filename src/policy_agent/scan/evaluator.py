"""Pure evaluation of a single policy against a single resource snapshot."""

from __future__ import annotations

from policy_agent.policy.conditions import evaluate_condition
from policy_agent.policy.model import Effect, Policy
from policy_agent.scan.results import Finding, ResourceSnapshot


def evaluate_resource(policy: Policy, snapshot: ResourceSnapshot) -> Finding | None:
    """Evaluate one policy against one resource snapshot.

    A policy that targets a different resource type, or whose optional ``match`` selector
    excludes the resource, does not apply and yields no finding.

    Args:
        policy: The policy to evaluate.
        snapshot: The resource snapshot to evaluate against.

    Returns:
        A `Finding` describing the outcome, or ``None`` when the policy does not
        apply to this resource.
    """
    if policy.resource_type is not snapshot.resource_type:
        return None
    if policy.match is not None and not evaluate_condition(policy.match, snapshot.attributes):
        return None

    rule_matches = evaluate_condition(policy.rule, snapshot.attributes)
    compliant = rule_matches if policy.effect is Effect.ALLOW else not rule_matches
    return Finding(
        policy_name=policy.name,
        resource_type=snapshot.resource_type,
        resource_id=snapshot.resource_id,
        resource_name=snapshot.name,
        compliant=compliant,
        effect=policy.effect,
        enforcement=policy.enforcement,
        message=_describe(policy, compliant),
        remediation="" if compliant else policy.remediation,
        owner=snapshot.owner,
    )


def _describe(policy: Policy, compliant: bool) -> str:
    if compliant:
        return f"Complies with policy {policy.name!r}."
    if policy.effect is Effect.DENY:
        return f"Matches denied configuration of policy {policy.name!r}."
    return f"Does not satisfy required configuration of policy {policy.name!r}."
