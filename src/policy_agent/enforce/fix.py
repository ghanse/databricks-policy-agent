"""Suggested remediations for violating declared resources.

Because the gate evaluates the *resolved* bundle (variables and target overrides already
applied), it cannot always map a change back to the exact line of templated source. So v1
mutation surfaces the policy's authored remediation guidance per violating resource — a
suggestion an author applies — rather than silently rewriting ``databricks.yml``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from policy_agent.enforce.model import FixSuggestion
from policy_agent.policy.model import Policy
from policy_agent.scan.results import Finding


def suggest_fixes(
    violations: Iterable[Finding], policies_by_name: Mapping[str, Policy]
) -> tuple[FixSuggestion, ...]:
    """Build a remediation suggestion for each violation.

    Args:
        violations: The violating findings.
        policies_by_name: Policies keyed by name, used to source remediation guidance.

    Returns:
        One `FixSuggestion` per violation, in order.
    """
    suggestions = []
    for violation in violations:
        policy = policies_by_name.get(violation.policy_name)
        guidance = policy.remediation if policy and policy.remediation else violation.message
        suggestions.append(
            FixSuggestion(
                policy_name=violation.policy_name,
                resource_type=violation.resource_type,
                resource_id=violation.resource_id,
                guidance=guidance,
            )
        )
    return tuple(suggestions)
