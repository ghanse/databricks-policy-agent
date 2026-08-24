"""Evaluate declared bundle resources against policies and decide a gate verdict.

The gate reuses the scan evaluator (:func:`evaluate_resource`) — the only difference from a
live scan is the source of the snapshots. Enforcement levels decide the verdict: ``advisory``
violations only warn, ``soft`` violations block unless overridden, and ``hard`` violations
block and cannot be overridden.
"""

from __future__ import annotations

from collections.abc import Iterable

from policy_agent.enforce.fix import suggest_fixes
from policy_agent.enforce.model import FixSuggestion, GateResult, GateVerdict
from policy_agent.policy.model import EnforcementLevel, Policy, meets_threshold
from policy_agent.scan.evaluator import evaluate_resource
from policy_agent.scan.results import ResourceSnapshot


def run_gate(
    policies: Iterable[Policy],
    snapshots: Iterable[ResourceSnapshot],
    *,
    fail_on: EnforcementLevel = EnforcementLevel.HARD,
    overrides: frozenset[str] = frozenset(),
    override_reason: str = "",
    suggest_remediations: bool = False,
) -> GateResult:
    """Gate declared resources against policies.

    Args:
        policies: The policies to enforce.
        snapshots: Declared-resource snapshots (see :func:`snapshot_bundle`).
        fail_on: Minimum enforcement level that blocks (``advisory`` blocks everything,
            ``hard`` blocks only hard violations).
        overrides: Policy names to override; only ``soft`` violations can be overridden.
        override_reason: Reason recorded for the overrides.
        suggest_remediations: When ``True``, attach remediation suggestions for violations.

    Returns:
        The :class:`GateResult` describing the verdict and categorised violations.
    """
    policy_list = list(policies)
    snapshot_list = list(snapshots)
    violations = [
        finding
        for policy in policy_list
        for snapshot in snapshot_list
        if (finding := evaluate_resource(policy, snapshot)) is not None and not finding.compliant
    ]

    blocking = []
    overridden = []
    warnings = []
    for violation in violations:
        if not meets_threshold(violation.enforcement, fail_on):
            warnings.append(violation)
        elif violation.enforcement is EnforcementLevel.SOFT and violation.policy_name in overrides:
            overridden.append(violation)
        else:
            blocking.append(violation)

    if blocking:
        verdict = GateVerdict.BLOCKED
    elif warnings or overridden:
        verdict = GateVerdict.PASS_WITH_WARNINGS
    else:
        verdict = GateVerdict.PASS

    fixes: tuple[FixSuggestion, ...] = ()
    if suggest_remediations:
        by_name = {policy.name: policy for policy in policy_list}
        fixes = suggest_fixes(violations, by_name)

    return GateResult(
        verdict=verdict,
        violations=tuple(violations),
        blocking=tuple(blocking),
        overridden=tuple(overridden),
        warnings=tuple(warnings),
        fixes=fixes,
        override_reason=override_reason,
    )
