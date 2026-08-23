"""Structural validation of policies and condition trees.

Validation guarantees a policy can be evaluated safely: every leaf names a registered
operator and an attribute the target resource type actually exposes. This is what makes the
declarative model safe — an unrecognised operator or attribute is rejected at author time
rather than silently ignored during a scan.
"""

from __future__ import annotations

from policy_agent.errors import InvalidPolicyError, UnknownConditionError
from policy_agent.policy.conditions import is_registered_operator
from policy_agent.policy.model import (
    RESOURCE_ATTRIBUTES,
    AllOf,
    AnyOf,
    Comparison,
    Condition,
    Negation,
    Policy,
    ResourceType,
    base_attribute,
)


def validate_policy(policy: Policy) -> None:
    """Validate a policy's identity and both of its condition trees.

    Args:
        policy: The policy to validate.

    Raises:
        InvalidPolicyError: If the name is empty or an attribute is invalid for the type.
        UnknownConditionError: If any leaf references an unregistered operator.
    """
    if not policy.name.strip():
        raise InvalidPolicyError("Policy name must be a non-empty string.")
    validate_condition(policy.rule, policy.resource_type)
    if policy.match is not None:
        validate_condition(policy.match, policy.resource_type)


def validate_condition(condition: Condition, resource_type: ResourceType) -> None:
    """Recursively validate a condition tree against a resource type's attributes.

    Args:
        condition: The condition tree to validate.
        resource_type: The resource type whose attribute set leaves are checked against.

    Raises:
        InvalidPolicyError: If a leaf names an attribute the resource type does not expose.
        UnknownConditionError: If a leaf references an unregistered operator.
    """
    if isinstance(condition, Comparison):
        _validate_comparison(condition, resource_type)
        return
    if isinstance(condition, AllOf | AnyOf):
        for child in condition.conditions:
            validate_condition(child, resource_type)
        return
    if isinstance(condition, Negation):
        validate_condition(condition.condition, resource_type)
        return
    raise UnknownConditionError(f"Unsupported condition node: {type(condition).__name__}")


def _validate_comparison(comparison: Comparison, resource_type: ResourceType) -> None:
    if not is_registered_operator(comparison.operator):
        raise UnknownConditionError(f"Unknown operator: {comparison.operator!r}")
    known_attributes = RESOURCE_ATTRIBUTES[resource_type]
    if base_attribute(comparison.attribute) not in known_attributes:
        raise InvalidPolicyError(
            f"Attribute {comparison.attribute!r} is not valid for resource type "
            f"{resource_type.value!r}. Known attributes: {sorted(known_attributes)}."
        )
