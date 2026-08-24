"""Result types for the deployment-time enforcement gate.

The gate evaluates the same policies as a scan, but against resources *declared* in a
Databricks Asset Bundle rather than live workspace objects. Its verdict decides whether a
deployment pipeline should proceed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from policy_agent.policy.model import ResourceType
from policy_agent.scan.results import Finding


class GateVerdict(str, Enum):
    """Outcome of an enforcement gate over a bundle."""

    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class FixSuggestion:
    """A suggested remediation for one violating declared resource.

    Attributes:
        policy_name: The violated policy.
        resource_type: Type of the declared resource.
        resource_id: Bundle key / name of the declared resource.
        guidance: Human-readable guidance (the policy's remediation text when available).
    """

    policy_name: str
    resource_type: ResourceType
    resource_id: str
    guidance: str


@dataclass(frozen=True)
class GateResult:
    """The outcome of gating a bundle's declared resources against policies.

    Attributes:
        verdict: Overall gate verdict.
        violations: Every violating (policy, resource) evaluation.
        blocking: Violations that block the deployment.
        overridden: Soft violations waved through by an override.
        warnings: Violations below the fail-on threshold (never block).
        fixes: Suggested remediations (populated when fixes are requested).
        override_reason: Reason recorded for any overrides applied.
    """

    verdict: GateVerdict
    violations: tuple[Finding, ...]
    blocking: tuple[Finding, ...]
    overridden: tuple[Finding, ...]
    warnings: tuple[Finding, ...]
    fixes: tuple[FixSuggestion, ...] = ()
    override_reason: str = ""

    @property
    def blocked(self) -> bool:
        """Whether the deployment should be blocked."""
        return self.verdict is GateVerdict.BLOCKED

    def to_dict(self) -> dict[str, object]:
        """Render a JSON-serialisable summary of the gate result.

        Returns:
            A mapping suitable for machine-readable gate output.
        """
        return {
            "verdict": self.verdict.value,
            "blocked": self.blocked,
            "counts": {
                "violations": len(self.violations),
                "blocking": len(self.blocking),
                "overridden": len(self.overridden),
                "warnings": len(self.warnings),
            },
            "blocking": [_finding_dict(finding) for finding in self.blocking],
            "overridden": [_finding_dict(finding) for finding in self.overridden],
            "warnings": [_finding_dict(finding) for finding in self.warnings],
            "fixes": [
                {
                    "policy": fix.policy_name,
                    "resource_type": fix.resource_type.value,
                    "resource": fix.resource_id,
                    "guidance": fix.guidance,
                }
                for fix in self.fixes
            ],
            "override_reason": self.override_reason,
        }


def _finding_dict(finding: Finding) -> dict[str, object]:
    return {
        "policy": finding.policy_name,
        "enforcement_level": finding.enforcement_level.value,
        "resource_type": finding.resource_type.value,
        "resource": finding.resource_id,
        "message": finding.message,
    }
