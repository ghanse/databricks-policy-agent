"""Scan output types: resource snapshots, findings, and aggregated summaries.

A scan produces one `Finding` per applicable (policy, resource) pair. Findings are the
atomic unit persisted to storage and rendered in the app; `ScanSummary` derives the
headline counts a dashboard shows without re-scanning.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from policy_agent.policy.model import Effect, EnforcementLevel, ResourceType


@dataclass(frozen=True)
class ResourceSnapshot:
    """A normalized, evaluable view of one workspace resource.

    Attributes:
        resource_type: The type of resource this snapshot describes.
        attributes: Flat mapping of attribute names to values that policy conditions read.
            Always contains the common attributes ``id``, ``name``, ``owner``,
            ``owner_type``, ``tags``, and ``created_time``.
    """

    resource_type: ResourceType
    attributes: Mapping[str, Any]

    @property
    def resource_id(self) -> str:
        """The resource's stable identifier."""
        return str(self.attributes.get("id", ""))

    @property
    def name(self) -> str:
        """The resource's display name."""
        return str(self.attributes.get("name", ""))

    @property
    def owner(self) -> str | None:
        """The resource's owner principal, if known."""
        owner = self.attributes.get("owner")
        return str(owner) if owner is not None else None


@dataclass(frozen=True)
class Finding:
    """The outcome of evaluating one policy against one resource.

    Attributes:
        policy_name: Name of the evaluated policy.
        resource_type: Type of the evaluated resource.
        resource_id: Identifier of the evaluated resource.
        resource_name: Display name of the evaluated resource.
        compliant: ``True`` when the resource satisfies the policy.
        effect: The evaluated policy's effect.
        enforcement_level: The evaluated policy's enforcement level.
        message: Human-readable explanation of the outcome.
        remediation: Guidance for resolving a violation (empty when compliant).
        owner: The resource owner principal, if known.
    """

    policy_name: str
    resource_type: ResourceType
    resource_id: str
    resource_name: str
    compliant: bool
    effect: Effect
    enforcement_level: EnforcementLevel
    message: str
    remediation: str = ""
    owner: str | None = None


@dataclass(frozen=True)
class ScanSummary:
    """Aggregated counts derived from a scan's findings.

    Attributes:
        evaluated: Total number of (policy, resource) evaluations performed.
        compliant: Number of evaluations that were compliant.
        violations: Number of evaluations that were violations.
        violations_by_enforcement_level: Violation counts keyed by enforcement level.
        violations_by_resource_type: Violation counts keyed by resource-type value.
    """

    evaluated: int
    compliant: int
    violations: int
    violations_by_enforcement_level: Mapping[str, int]
    violations_by_resource_type: Mapping[str, int]

    @property
    def compliance_rate(self) -> float:
        """Fraction of evaluations that were compliant, in the range ``[0.0, 1.0]``."""
        return self.compliant / self.evaluated if self.evaluated else 1.0


@dataclass(frozen=True)
class ScanResult:
    """The complete result of a single scan run.

    Attributes:
        scan_id: Unique identifier for this scan run.
        started_at: When the scan began.
        finished_at: When the scan completed.
        findings: Every applicable (policy, resource) evaluation.
        policy_names: Names of the policies included in the scan.
        resource_types: Resource types included in the scan.
    """

    scan_id: str
    started_at: datetime
    finished_at: datetime
    findings: tuple[Finding, ...]
    policy_names: tuple[str, ...] = field(default_factory=tuple)
    resource_types: tuple[ResourceType, ...] = field(default_factory=tuple)

    @property
    def violations(self) -> tuple[Finding, ...]:
        """The subset of findings that are violations."""
        return tuple(finding for finding in self.findings if not finding.compliant)

    def summary(self) -> ScanSummary:
        """Computes the aggregated summary for this scan.

        Returns:
            A `ScanSummary` describing evaluation and violation counts.
        """
        violations = self.violations
        by_enforcement_level: Counter[str] = Counter(
            finding.enforcement_level.value for finding in violations
        )
        by_resource_type: Counter[str] = Counter(
            finding.resource_type.value for finding in violations
        )
        return ScanSummary(
            evaluated=len(self.findings),
            compliant=len(self.findings) - len(violations),
            violations=len(violations),
            violations_by_enforcement_level=dict(by_enforcement_level),
            violations_by_resource_type=dict(by_resource_type),
        )
