"""Round-trip checks over the shipped ``examples/*.yaml`` policies.

These guard against an example that no longer parses, references an attribute or operator a
resource type does not expose, or (for the properties example) silently never matches because a
dotted path fails to resolve a literal dotted key.
"""

from pathlib import Path

import pytest

from policy_agent.policy import load_policies_from_yaml, validate_policy
from policy_agent.policy.model import ResourceType
from policy_agent.scan.evaluator import evaluate_resource
from policy_agent.scan.results import ResourceSnapshot

_EXAMPLES_DIR = Path(__file__).parents[2] / "examples"


@pytest.mark.parametrize("example", sorted(_EXAMPLES_DIR.glob("*.yaml")), ids=lambda p: p.name)
def test_example_policies_load_and_validate(example):
    policies = load_policies_from_yaml(example)
    assert policies, f"{example.name} declares no policies"
    for policy in policies:
        validate_policy(policy)


def test_change_data_feed_example_resolves_dotted_property_key():
    # Regression guard: the property key is the literal dotted string "delta.enableChangeDataFeed",
    # so this policy is only meaningful if a dotted path resolves it. A table with the property set
    # must be compliant and one without it must violate.
    policies = load_policies_from_yaml(_EXAMPLES_DIR / "tables.yaml")
    policy = next(p for p in policies if p.name == "prod-tables-must-enable-change-data-feed")

    base = {
        "id": "prod.sales.orders",
        "name": "orders",
        "catalog_name": "prod",
        "data_source_format": "DELTA",
    }
    enabled = ResourceSnapshot(
        ResourceType.TABLE, {**base, "properties": {"delta.enableChangeDataFeed": "true"}}
    )
    disabled = ResourceSnapshot(ResourceType.TABLE, {**base, "properties": {}})

    assert evaluate_resource(policy, enabled).compliant is True
    assert evaluate_resource(policy, disabled).compliant is False
