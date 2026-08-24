"""Round-trip conversion between policies and plain dictionaries.

Dictionaries are the interchange format shared by the YAML loader, the storage backends,
and the app's JSON API. Keeping conversion in one module guarantees every surface encodes
policies identically.
"""

from __future__ import annotations

from typing import Any

from policy_agent.errors import InvalidPolicyError
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


def policy_from_dict(data: dict[str, Any]) -> Policy:
    """Build a policy from a plain dictionary (e.g. parsed YAML or a JSON request body).

    Args:
        data: Mapping with keys ``policy``/``name``, ``resource_type``, ``effect``, and
            ``rule``, plus optional ``description``, ``enforcement``, ``match``,
            ``remediation``, ``status``, and ``version``.

    Returns:
        The constructed :class:`Policy`.

    Raises:
        InvalidPolicyError: If a required key is missing or an enum value is unrecognised.
    """
    name = data.get("policy") or data.get("name")
    if not name:
        raise InvalidPolicyError("Policy dictionary must include a 'policy' (or 'name') key.")
    match = data.get("match")
    try:
        return Policy(
            name=str(name),
            resource_type=ResourceType(_require(data, "resource_type", name)),
            effect=Effect(_require(data, "effect", name)),
            rule=condition_from_dict(_require(data, "rule", name)),
            description=str(data.get("description", "")),
            enforcement=EnforcementLevel(data.get("enforcement", EnforcementLevel.ADVISORY.value)),
            match=condition_from_dict(match) if match is not None else None,
            remediation=str(data.get("remediation", "")),
            status=PolicyStatus(data.get("status", PolicyStatus.DRAFT.value)),
            version=int(data.get("version", 1)),
        )
    except ValueError as error:
        raise InvalidPolicyError(f"Invalid value in policy {name!r}: {error}") from error


def policy_to_dict(policy: Policy) -> dict[str, Any]:
    """Serialise a policy to a plain dictionary with enum values rendered as strings.

    Args:
        policy: The policy to serialise.

    Returns:
        A dictionary suitable for YAML/JSON encoding and storage.
    """
    data: dict[str, Any] = {
        "policy": policy.name,
        "resource_type": policy.resource_type.value,
        "effect": policy.effect.value,
        "enforcement": policy.enforcement.value,
        "status": policy.status.value,
        "version": policy.version,
        "rule": condition_to_dict(policy.rule),
    }
    if policy.description:
        data["description"] = policy.description
    if policy.match is not None:
        data["match"] = condition_to_dict(policy.match)
    if policy.remediation:
        data["remediation"] = policy.remediation
    return data


def condition_from_dict(node: dict[str, Any]) -> Condition:
    """Parse a condition tree from its dictionary form.

    Args:
        node: A mapping shaped as one of ``{"all": [...]}``, ``{"any": [...]}``,
            ``{"not": {...}}``, or a leaf ``{"attribute": ..., "operator": ..., "value": ...}``.

    Returns:
        The parsed condition node.

    Raises:
        InvalidPolicyError: If the node shape is not recognised or a leaf omits keys.
    """
    if not isinstance(node, dict):
        raise InvalidPolicyError(f"Condition must be a mapping, got {type(node).__name__}.")
    if "all" in node:
        return AllOf(tuple(condition_from_dict(child) for child in node["all"]))
    if "any" in node:
        return AnyOf(tuple(condition_from_dict(child) for child in node["any"]))
    if "not" in node:
        return Negation(condition_from_dict(node["not"]))
    if "attribute" in node and "operator" in node:
        return Comparison(node["attribute"], node["operator"], node.get("value"))
    raise InvalidPolicyError(
        "Condition must be one of 'all', 'any', 'not', or a leaf with 'attribute' and "
        f"'operator' keys; got keys {sorted(node)}."
    )


def condition_to_dict(condition: Condition) -> dict[str, Any]:
    """Serialise a condition tree to its dictionary form.

    Args:
        condition: The condition node to serialise.

    Returns:
        The dictionary representation of the condition tree.

    Raises:
        InvalidPolicyError: If the condition is an unsupported node type.
    """
    if isinstance(condition, Comparison):
        leaf: dict[str, Any] = {"attribute": condition.attribute, "operator": condition.operator}
        if condition.value is not None:
            leaf["value"] = condition.value
        return leaf
    if isinstance(condition, AllOf):
        return {"all": [condition_to_dict(child) for child in condition.conditions]}
    if isinstance(condition, AnyOf):
        return {"any": [condition_to_dict(child) for child in condition.conditions]}
    if isinstance(condition, Negation):
        return {"not": condition_to_dict(condition.condition)}
    raise InvalidPolicyError(f"Unsupported condition node: {type(condition).__name__}")


def _require(data: dict[str, Any], key: str, policy_name: Any) -> Any:
    if key not in data:
        raise InvalidPolicyError(f"Policy {policy_name!r} is missing required key {key!r}.")
    return data[key]
