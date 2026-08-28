import pytest

from policy_agent.errors import (
    InvalidPolicyError,
    UnknownConditionError,
    UnsupportedResourceError,
)
from policy_agent.policy import (
    Effect,
    EnforcementLevel,
    PolicyStatus,
    ResourceType,
    all_of,
    allow,
    any_of,
    deny,
    dump_policies_to_yaml,
    leaf,
    load_policies_from_yaml,
    not_,
    policy_from_dict,
    policy_to_dict,
    referenced_attributes,
    validate_policy,
)
from policy_agent.policy.model import RESOURCE_ATTRIBUTES, TAGGABLE_RESOURCE_TYPES

CLUSTER_YAML = """
policy: only-service-principals-own-compute
description: All-purpose clusters must be owned by a service principal.
resource_type: cluster
effect: deny
enforcement_level: hard
match:
  all:
    - { attribute: cluster_source, operator: equals, value: UI }
rule:
  any:
    - { attribute: owner_type, operator: not_equals, value: service_principal }
remediation: Transfer cluster ownership to an approved service principal.
"""


def test_deny_and_allow_set_effect_and_coerce_strings():
    denied = deny(
        "n", "cluster", any_of(leaf("owner_type", "equals", "user")), enforcement_level="hard"
    )
    allowed = allow("m", ResourceType.JOB, leaf("name", "matches_regex", "^prod_.+$"))
    assert denied.effect is Effect.DENY
    assert denied.resource_type is ResourceType.CLUSTER
    assert denied.enforcement_level is EnforcementLevel.HARD
    assert denied.status is PolicyStatus.DRAFT
    assert allowed.effect is Effect.ALLOW


def test_load_yaml_parses_match_and_rule():
    policies = load_policies_from_yaml(CLUSTER_YAML)
    assert len(policies) == 1
    parsed = policies[0]
    assert parsed.name == "only-service-principals-own-compute"
    assert parsed.effect is Effect.DENY
    assert parsed.match is not None
    assert parsed.remediation.startswith("Transfer")


def test_yaml_round_trip_is_stable():
    original = load_policies_from_yaml(CLUSTER_YAML)
    reparsed = load_policies_from_yaml(dump_policies_to_yaml(original))
    assert original == reparsed


def test_dict_round_trip_preserves_policy():
    original = deny(
        "job-naming",
        "job",
        all_of(leaf("name", "matches_regex", "^(prod|dev)_.+$")),
        description="Naming convention",
        remediation="Rename the job.",
    )
    assert policy_from_dict(policy_to_dict(original)) == original


def test_multi_document_yaml_and_list_form():
    text = """
- policy: a
  resource_type: job
  effect: allow
  rule: { attribute: name, operator: exists }
---
policy: b
resource_type: app
effect: deny
rule: { attribute: owner_type, operator: not_equals, value: service_principal }
"""
    policies = load_policies_from_yaml(text)
    assert [p.name for p in policies] == ["a", "b"]


def test_validate_rejects_unknown_attribute():
    invalid = deny("bad", "job", leaf("nonexistent_attr", "equals", "x"))
    with pytest.raises(InvalidPolicyError):
        validate_policy(invalid)


def test_validate_allows_tags_on_taggable_genie_space():
    # Genie spaces are tagged through workspace tag assignments, so `tags` is in their attribute
    # set and a policy that references it is valid at author time.
    valid = deny("genie-tagged", "genie_space", leaf("tags", "not_empty"))
    validate_policy(valid)


def test_validate_rejects_unknown_operator():
    invalid = deny("bad", "job", leaf("name", "sounds_like", "x"))
    with pytest.raises(UnknownConditionError):
        validate_policy(invalid)


def test_validate_rejects_blank_name():
    with pytest.raises(InvalidPolicyError):
        validate_policy(deny("   ", "job", leaf("name", "exists")))


def test_load_rejects_missing_required_key():
    with pytest.raises(InvalidPolicyError):
        load_policies_from_yaml("policy: x\nresource_type: job\neffect: deny\n")


def test_load_rejects_unknown_resource_type():
    with pytest.raises(UnsupportedResourceError):
        policy_from_dict(
            {
                "policy": "x",
                "resource_type": "notebook",
                "effect": "deny",
                "rule": {"attribute": "name", "operator": "exists"},
            }
        )


def test_referenced_attributes_collects_across_rule_and_match():
    p = deny(
        "tagged-serverless",
        "job",
        all_of(
            leaf("has_retry_policy", "equals", True),
            any_of(leaf("tags.team", "exists"), leaf("uses_serverless_compute", "equals", True)),
        ),
        match=leaf("name", "matches_regex", "^prod_.+$"),
    )
    # Dotted paths reduce to their base, and both trees contribute.
    assert referenced_attributes(p) == frozenset(
        {"has_retry_policy", "tags", "uses_serverless_compute", "name"}
    )


def test_referenced_attributes_handles_negation_and_no_match():
    p = allow("no-serverless", "job", not_(leaf("uses_serverless_compute", "equals", True)))
    assert referenced_attributes(p) == frozenset({"uses_serverless_compute"})


@pytest.mark.parametrize("resource_type", ["secret_scope", "registered_model", "quality_monitor"])
def test_validate_rejects_tags_on_non_taggable_types(resource_type):
    invalid = deny("bad", resource_type, leaf("tags", "not_empty"))
    with pytest.raises(InvalidPolicyError):
        validate_policy(invalid)


def test_taggability_is_consistent_with_attribute_sets():
    for resource_type, attributes in RESOURCE_ATTRIBUTES.items():
        assert ("tags" in attributes) == (resource_type in TAGGABLE_RESOURCE_TYPES)
