import pytest

from policy_agent.errors import UnknownConditionError
from policy_agent.policy import all_of, any_of, evaluate_condition, leaf, not_
from policy_agent.policy.conditions import registered_operators, resolve_attribute


@pytest.mark.parametrize(
    ("operator", "value", "actual", "expected"),
    [
        ("equals", "prod", "prod", True),
        ("equals", "prod", "dev", False),
        ("not_equals", "prod", "dev", True),
        ("matches_regex", r"^prod_.+$", "prod_etl", True),
        ("matches_regex", r"^prod_.+$", "dev_etl", False),
        ("in", ["a", "b"], "b", True),
        ("in", ["a", "b"], "c", False),
        ("not_in", ["a", "b"], "c", True),
        ("exists", None, "anything", True),
        ("exists", None, None, False),
        ("absent", None, None, True),
        ("less_than", 60, 30, True),
        ("less_than", 60, 90, False),
        ("greater_than", 1, 2, True),
        ("ttl_within", 120, 60, True),
        ("ttl_within", 120, 0, False),
    ],
)
def test_operator_semantics(operator, value, actual, expected):
    condition = leaf("name", operator, value)
    assert evaluate_condition(condition, {"name": actual}) is expected


def test_owner_is_service_principal_operator():
    condition = leaf("owner_type", "owner_is_service_principal")
    assert evaluate_condition(condition, {"owner_type": "service_principal"}) is True
    assert evaluate_condition(condition, {"owner_type": "user"}) is False


def test_has_and_missing_tag_operate_on_mapping():
    snapshot = {"tags": {"cost_center": "42"}}
    assert evaluate_condition(leaf("tags", "has_tag", "cost_center"), snapshot) is True
    assert evaluate_condition(leaf("tags", "missing_tag", "team"), snapshot) is True
    assert evaluate_condition(leaf("tags", "has_tag", "team"), snapshot) is False


def test_not_empty_operator():
    assert evaluate_condition(leaf("tags", "not_empty"), {"tags": {"env": "prod"}}) is True
    assert evaluate_condition(leaf("tags", "not_empty"), {"tags": {}}) is False
    assert evaluate_condition(leaf("tags", "not_empty"), {"tags": None}) is False


def test_boolean_is_not_treated_as_number():
    assert evaluate_condition(leaf("flag", "less_than", 5), {"flag": True}) is False


def test_dotted_attribute_resolution():
    snapshot = {"tags": {"environment": "prod"}}
    assert resolve_attribute(snapshot, "tags.environment") == "prod"
    assert resolve_attribute(snapshot, "tags.missing") is None
    assert resolve_attribute(snapshot, "missing.deep") is None


def test_nested_boolean_logic():
    rule = all_of(
        leaf("owner_type", "not_equals", "service_principal"),
        any_of(
            leaf("cluster_source", "equals", "UI"),
            not_(leaf("autotermination_minutes", "exists")),
        ),
    )
    matching = {"owner_type": "user", "cluster_source": "UI", "autotermination_minutes": 30}
    non_matching = {"owner_type": "service_principal", "cluster_source": "UI"}
    assert evaluate_condition(rule, matching) is True
    assert evaluate_condition(rule, non_matching) is False


def test_empty_all_is_true_empty_any_is_false():
    assert evaluate_condition(all_of(), {}) is True
    assert evaluate_condition(any_of(), {}) is False


def test_unknown_operator_raises():
    with pytest.raises(UnknownConditionError):
        evaluate_condition(leaf("name", "sounds_like", "prod"), {"name": "prod"})


def test_registered_operators_are_sorted_and_complete():
    operators = registered_operators()
    assert operators == tuple(sorted(operators))
    assert "equals" in operators and "ttl_within" in operators
