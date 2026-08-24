"""Core policy data model: resource types, effects, condition trees, and policies.

Policies are immutable, declarative data. A policy pairs a *condition tree* with an
:class:`Effect` (allow or deny) over one :class:`ResourceType`. Condition trees are built
from a small set of frozen node types (:class:`Comparison`, :class:`AllOf`, :class:`AnyOf`,
:class:`Negation`) so evaluation is a pure walk over data with no code execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResourceType(str, Enum):
    """A Databricks workspace object type a policy can target."""

    JOB = "job"
    CLUSTER = "cluster"
    SQL_WAREHOUSE = "sql_warehouse"
    APP = "app"
    SERVING_ENDPOINT = "serving_endpoint"


class Effect(str, Enum):
    """Whether matching a policy's rule means a resource is compliant or violating.

    ``ALLOW`` policies are allow-lists: a resource is compliant only when its rule matches.
    ``DENY`` policies are deny-lists: a resource violates the policy when its rule matches.
    """

    ALLOW = "allow"
    DENY = "deny"


class Severity(str, Enum):
    """Relative importance of a policy violation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyStatus(str, Enum):
    """Lifecycle state of a policy in the draft-review-approve workflow."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Condition:
    """Base type for every node in a policy condition tree."""


@dataclass(frozen=True)
class Comparison(Condition):
    """A leaf condition comparing one resource attribute against an expected value.

    Attributes:
        attribute: Name of the resource-snapshot attribute to read. Dotted paths such as
            ``tags.environment`` index into nested mappings.
        operator: Name of a registered operator (see :mod:`policy_agent.policy.conditions`).
        value: The expected value the operator compares the attribute against. Operators
            such as ``exists`` and ``absent`` ignore it.
    """

    attribute: str
    operator: str
    value: object = None


@dataclass(frozen=True)
class AllOf(Condition):
    """A conjunction that holds only when every child condition holds.

    Attributes:
        conditions: Child conditions; an empty tuple evaluates to ``True``.
    """

    conditions: tuple[Condition, ...]


@dataclass(frozen=True)
class AnyOf(Condition):
    """A disjunction that holds when at least one child condition holds.

    Attributes:
        conditions: Child conditions; an empty tuple evaluates to ``False``.
    """

    conditions: tuple[Condition, ...]


@dataclass(frozen=True)
class Negation(Condition):
    """A negation that holds when its child condition does not.

    Attributes:
        condition: The child condition whose truth value is inverted.
    """

    condition: Condition


@dataclass(frozen=True)
class Policy:
    """An immutable compliance policy over a single resource type.

    Attributes:
        name: Unique, human-readable policy identifier (kebab-case by convention).
        resource_type: The workspace object type this policy is evaluated against.
        effect: Whether a rule match means compliant (``ALLOW``) or violating (``DENY``).
        rule: The condition tree evaluated against each resource snapshot.
        description: Free-text explanation of the policy's intent.
        severity: Importance assigned to violations of this policy.
        match: Optional selector narrowing which resources the policy applies to; when
            ``None`` the policy applies to every resource of ``resource_type``.
        remediation: Guidance shown to owners on how to bring a resource into compliance.
        status: Position of the policy in the approval lifecycle.
        version: Monotonic version incremented on each approved change.
    """

    name: str
    resource_type: ResourceType
    effect: Effect
    rule: Condition
    description: str = ""
    severity: Severity = Severity.MEDIUM
    match: Condition | None = None
    remediation: str = ""
    status: PolicyStatus = PolicyStatus.DRAFT
    version: int = 1


COMMON_RESOURCE_ATTRIBUTES: frozenset[str] = frozenset(
    {"id", "name", "owner", "owner_type", "tags", "created_time"}
)
"""Attributes every resource snapshot exposes, regardless of resource type."""


RESOURCE_ATTRIBUTES: dict[ResourceType, frozenset[str]] = {
    ResourceType.JOB: COMMON_RESOURCE_ATTRIBUTES
    | {
        "schedule_pause_status",
        "max_concurrent_runs",
        "timeout_seconds",
        "run_as_type",
        "has_email_notifications",
        "has_retry_policy",
        "uses_serverless_compute",
        "format",
    },
    ResourceType.CLUSTER: COMMON_RESOURCE_ATTRIBUTES
    | {
        "cluster_source",
        "autotermination_minutes",
        "spark_version",
        "node_type_id",
        "num_workers",
        "data_security_mode",
        "single_user_name",
    },
    ResourceType.SQL_WAREHOUSE: COMMON_RESOURCE_ATTRIBUTES
    | {
        "warehouse_type",
        "cluster_size",
        "auto_stop_minutes",
        "enable_serverless_compute",
        "min_num_clusters",
        "max_num_clusters",
    },
    ResourceType.APP: COMMON_RESOURCE_ATTRIBUTES
    | {
        "app_status",
        "compute_status",
        "active_deployment_mode",
    },
    ResourceType.SERVING_ENDPOINT: COMMON_RESOURCE_ATTRIBUTES
    | {
        "endpoint_state",
        "endpoint_type",
        "budget_policy_id",
        "route_optimized",
    },
}
"""Attributes each resource type exposes; the contract scanning must satisfy and the set
policy validation checks attribute names against."""


OWNER_TYPE_SERVICE_PRINCIPAL: str = "service_principal"
OWNER_TYPE_USER: str = "user"
OWNER_TYPE_GROUP: str = "group"
OWNER_TYPE_UNKNOWN: str = "unknown"


def base_attribute(attribute: str) -> str:
    """Return the top-level attribute name from a possibly dotted attribute path.

    Args:
        attribute: An attribute name such as ``tags`` or a dotted path such as
            ``tags.environment``.

    Returns:
        The portion of ``attribute`` before the first dot.
    """
    return attribute.split(".", 1)[0]


def referenced_attributes(policy: Policy) -> frozenset[str]:
    """Return the base attribute names a policy reads across its rule and match trees.

    Lets a scanner fetch only the data a policy actually inspects — for example, skipping an
    expensive expansion when no active policy references an attribute derived from it.

    Args:
        policy: The policy to inspect.

    Returns:
        The set of top-level attribute names (dotted paths reduced to their base) named by
        any leaf in the policy's ``rule`` or ``match`` condition trees.
    """
    names: set[str] = set()
    _collect_attributes(policy.rule, names)
    if policy.match is not None:
        _collect_attributes(policy.match, names)
    return frozenset(names)


def _collect_attributes(condition: Condition, names: set[str]) -> None:
    if isinstance(condition, Comparison):
        names.add(base_attribute(condition.attribute))
    elif isinstance(condition, AllOf | AnyOf):
        for child in condition.conditions:
            _collect_attributes(child, names)
    elif isinstance(condition, Negation):
        _collect_attributes(condition.condition, names)
