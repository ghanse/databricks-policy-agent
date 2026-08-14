"""Condition evaluation and the registry of comparison operators.

Evaluating a condition tree is a pure walk over a resource snapshot (a flat mapping of
attribute names to values). Leaf comparisons delegate to named operators drawn from a fixed
registry, so no policy can execute arbitrary code — the entire operator vocabulary is the
functions in :data:`OPERATORS`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from policy_agent.errors import UnknownConditionError
from policy_agent.policy.model import (
    OWNER_TYPE_SERVICE_PRINCIPAL,
    AllOf,
    AnyOf,
    Comparison,
    Condition,
    Negation,
)

Snapshot = Mapping[str, Any]
Operator = Callable[[Any, Any], bool]


def evaluate_condition(condition: Condition, snapshot: Snapshot) -> bool:
    """Evaluate a condition tree against a single resource snapshot.

    Args:
        condition: The condition tree to evaluate.
        snapshot: Flat mapping of resource attributes; dotted attribute paths index into
            nested mappings.

    Returns:
        ``True`` when the condition holds for the snapshot, otherwise ``False``.

    Raises:
        UnknownConditionError: If a leaf references an operator absent from the registry.
    """
    if isinstance(condition, Comparison):
        operator = _require_operator(condition.operator)
        actual = resolve_attribute(snapshot, condition.attribute)
        return operator(actual, condition.value)
    if isinstance(condition, AllOf):
        return all(evaluate_condition(child, snapshot) for child in condition.conditions)
    if isinstance(condition, AnyOf):
        return any(evaluate_condition(child, snapshot) for child in condition.conditions)
    if isinstance(condition, Negation):
        return not evaluate_condition(condition.condition, snapshot)
    raise UnknownConditionError(f"Unsupported condition node: {type(condition).__name__}")


def resolve_attribute(snapshot: Snapshot, attribute: str) -> Any:
    """Read an attribute from a snapshot, following dotted paths into nested mappings.

    Args:
        snapshot: The resource snapshot.
        attribute: An attribute name or dotted path such as ``tags.environment``.

    Returns:
        The attribute value, or ``None`` when any path segment is missing.
    """
    current: Any = snapshot
    for segment in attribute.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            return None
        current = current[segment]
    return current


def is_registered_operator(name: str) -> bool:
    """Return whether ``name`` is a known comparison operator.

    Args:
        name: Candidate operator name.

    Returns:
        ``True`` if the operator exists in :data:`OPERATORS`.
    """
    return name in OPERATORS


def registered_operators() -> tuple[str, ...]:
    """Return the sorted names of every registered comparison operator.

    Returns:
        A tuple of operator names.
    """
    return tuple(sorted(OPERATORS))


def _require_operator(name: str) -> Operator:
    operator = OPERATORS.get(name)
    if operator is None:
        raise UnknownConditionError(f"Unknown operator: {name!r}")
    return operator


def _equals(actual: Any, expected: Any) -> bool:
    return actual == expected


def _not_equals(actual: Any, expected: Any) -> bool:
    return actual != expected


def _matches_regex(actual: Any, pattern: Any) -> bool:
    if actual is None:
        return False
    return re.search(str(pattern), str(actual)) is not None


def _in(actual: Any, expected: Any) -> bool:
    return isinstance(expected, list | tuple | set) and actual in expected


def _not_in(actual: Any, expected: Any) -> bool:
    return isinstance(expected, list | tuple | set) and actual not in expected


def _exists(actual: Any, _expected: Any) -> bool:
    return actual is not None


def _absent(actual: Any, _expected: Any) -> bool:
    return actual is None


def _less_than(actual: Any, expected: Any) -> bool:
    return _is_number(actual) and _is_number(expected) and actual < expected


def _greater_than(actual: Any, expected: Any) -> bool:
    return _is_number(actual) and _is_number(expected) and actual > expected


def _contains(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    try:
        return expected in actual
    except TypeError:
        return False


def _has_tag(actual: Any, tag_key: Any) -> bool:
    return isinstance(actual, Mapping) and tag_key in actual


def _missing_tag(actual: Any, tag_key: Any) -> bool:
    return not (isinstance(actual, Mapping) and tag_key in actual)


def _owner_is_service_principal(actual: Any, _expected: Any) -> bool:
    return actual == OWNER_TYPE_SERVICE_PRINCIPAL


def _ttl_within(actual: Any, max_seconds: Any) -> bool:
    return _is_number(actual) and _is_number(max_seconds) and 0 < actual <= max_seconds


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


OPERATORS: dict[str, Operator] = {
    "equals": _equals,
    "not_equals": _not_equals,
    "matches_regex": _matches_regex,
    "in": _in,
    "not_in": _not_in,
    "exists": _exists,
    "absent": _absent,
    "less_than": _less_than,
    "greater_than": _greater_than,
    "contains": _contains,
    "has_tag": _has_tag,
    "missing_tag": _missing_tag,
    "owner_is_service_principal": _owner_is_service_principal,
    "ttl_within": _ttl_within,
}
"""The complete vocabulary of comparison operators, keyed by the name policies reference."""
