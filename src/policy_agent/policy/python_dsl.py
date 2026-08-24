"""Functional constructors for declaring policies and condition trees in Python.

These helpers are thin, keyword-friendly wrappers over the frozen model types. They coerce
string inputs (resource type, enforcement_level) into their enums so callers can write policies
without importing every enum member.

Example:
    >>> from policy_agent.policy import deny, any_of, leaf, ResourceType
    >>> policy = deny(
    ...     name="only-service-principals-own-compute",
    ...     resource_type=ResourceType.CLUSTER,
    ...     rule=any_of(leaf("owner_type", "not_equals", "service_principal")),
    ... )
"""

from __future__ import annotations

from policy_agent.policy.model import (
    AllOf,
    AnyOf,
    Comparison,
    Condition,
    Effect,
    EnforcementLevel,
    Negation,
    Policy,
    PolicyStatus,
    ResourceType,
)


def deny(
    name: str,
    resource_type: ResourceType | str,
    rule: Condition,
    *,
    description: str = "",
    enforcement_level: EnforcementLevel | str = EnforcementLevel.ADVISORY,
    match: Condition | None = None,
    remediation: str = "",
    status: PolicyStatus | str = PolicyStatus.DRAFT,
    version: int = 1,
) -> Policy:
    """Build a deny-list policy: resources whose rule matches are violations.

    Args:
        name: Unique policy identifier.
        resource_type: Target resource type, as a `ResourceType` or its string value.
        rule: Condition tree whose match marks a resource as violating.
        description: Free-text explanation of intent.
        enforcement_level: How strongly the policy is enforced; an EnforcementLevel or its value.
        match: Optional selector limiting which resources the policy applies to.
        remediation: Guidance for bringing a resource into compliance.
        status: Initial approval-lifecycle status.
        version: Initial version number.

    Returns:
        A `Policy` with `Effect.DENY`.
    """
    return policy(
        name=name,
        resource_type=resource_type,
        effect=Effect.DENY,
        rule=rule,
        description=description,
        enforcement_level=enforcement_level,
        match=match,
        remediation=remediation,
        status=status,
        version=version,
    )


def allow(
    name: str,
    resource_type: ResourceType | str,
    rule: Condition,
    *,
    description: str = "",
    enforcement_level: EnforcementLevel | str = EnforcementLevel.ADVISORY,
    match: Condition | None = None,
    remediation: str = "",
    status: PolicyStatus | str = PolicyStatus.DRAFT,
    version: int = 1,
) -> Policy:
    """Build an allow-list policy: resources whose rule does not match are violations.

    Args:
        name: Unique policy identifier.
        resource_type: Target resource type, as a `ResourceType` or its string value.
        rule: Condition tree a compliant resource must match.
        description: Free-text explanation of intent.
        enforcement_level: How strongly the policy is enforced; an EnforcementLevel or its value.
        match: Optional selector limiting which resources the policy applies to.
        remediation: Guidance for bringing a resource into compliance.
        status: Initial approval-lifecycle status.
        version: Initial version number.

    Returns:
        A `Policy` with `Effect.ALLOW`.
    """
    return policy(
        name=name,
        resource_type=resource_type,
        effect=Effect.ALLOW,
        rule=rule,
        description=description,
        enforcement_level=enforcement_level,
        match=match,
        remediation=remediation,
        status=status,
        version=version,
    )


def policy(
    name: str,
    resource_type: ResourceType | str,
    effect: Effect | str,
    rule: Condition,
    *,
    description: str = "",
    enforcement_level: EnforcementLevel | str = EnforcementLevel.ADVISORY,
    match: Condition | None = None,
    remediation: str = "",
    status: PolicyStatus | str = PolicyStatus.DRAFT,
    version: int = 1,
) -> Policy:
    """Build a policy with an explicit effect, coercing string enum inputs.

    Args:
        name: Unique policy identifier.
        resource_type: Target resource type, as a `ResourceType` or its string value.
        effect: Whether a rule match means compliant (``allow``) or violating (``deny``).
        rule: The condition tree evaluated against each resource.
        description: Free-text explanation of intent.
        enforcement_level: How strongly the policy is enforced; an EnforcementLevel or its value.
        match: Optional selector limiting which resources the policy applies to.
        remediation: Guidance for bringing a resource into compliance.
        status: Initial approval-lifecycle status.
        version: Initial version number.

    Returns:
        The constructed `Policy`.
    """
    return Policy(
        name=name,
        resource_type=ResourceType(resource_type),
        effect=Effect(effect),
        rule=rule,
        description=description,
        enforcement_level=EnforcementLevel(enforcement_level),
        match=match,
        remediation=remediation,
        status=PolicyStatus(status),
        version=version,
    )


def leaf(attribute: str, operator: str, value: object = None) -> Comparison:
    """Build a leaf comparison condition.

    Args:
        attribute: Resource attribute name or dotted path (e.g. ``tags.environment``).
        operator: Registered operator name (e.g. ``equals``, ``matches_regex``).
        value: Expected value the operator compares against; unused by operators such as
            ``exists`` and ``absent``.

    Returns:
        A `Comparison` node.
    """
    return Comparison(attribute=attribute, operator=operator, value=value)


def all_of(*conditions: Condition) -> AllOf:
    """Build a conjunction that holds only when every child condition holds.

    Args:
        *conditions: Child conditions.

    Returns:
        An `AllOf` node.
    """
    return AllOf(conditions=tuple(conditions))


def any_of(*conditions: Condition) -> AnyOf:
    """Build a disjunction that holds when at least one child condition holds.

    Args:
        *conditions: Child conditions.

    Returns:
        An `AnyOf` node.
    """
    return AnyOf(conditions=tuple(conditions))


def not_(condition: Condition) -> Negation:
    """Build a negation that holds when its child condition does not.

    Args:
        condition: The condition to negate.

    Returns:
        A `Negation` node.
    """
    return Negation(condition=condition)
