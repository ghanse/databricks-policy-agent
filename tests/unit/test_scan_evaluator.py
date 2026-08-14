from policy_agent.policy import allow, deny, leaf
from policy_agent.policy.model import ResourceType
from policy_agent.scan.evaluator import evaluate_resource
from policy_agent.scan.results import ResourceSnapshot


def _cluster(**attributes):
    base = {"id": "c1", "name": "analytics", "owner_type": "user", "tags": {}}
    base.update(attributes)
    return ResourceSnapshot(ResourceType.CLUSTER, base)


def test_deny_policy_flags_matching_resource_as_violation():
    policy = deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    finding = evaluate_resource(policy, _cluster(owner_type="user"))
    assert finding is not None
    assert finding.compliant is False
    assert finding.remediation == policy.remediation
    assert "denied configuration" in finding.message


def test_deny_policy_passes_non_matching_resource():
    policy = deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    finding = evaluate_resource(policy, _cluster(owner_type="service_principal"))
    assert finding is not None
    assert finding.compliant is True
    assert finding.remediation == ""


def test_allow_policy_requires_rule_to_match():
    policy = allow("named", "cluster", leaf("name", "matches_regex", "^prod_.+$"))
    assert evaluate_resource(policy, _cluster(name="prod_etl")).compliant is True
    assert evaluate_resource(policy, _cluster(name="scratch")).compliant is False


def test_match_selector_excludes_non_matching_resource():
    policy = deny(
        "ui-clusters-need-sp",
        "cluster",
        leaf("owner_type", "not_equals", "service_principal"),
        match=leaf("cluster_source", "equals", "UI"),
    )
    assert evaluate_resource(policy, _cluster(cluster_source="JOB")) is None
    assert evaluate_resource(policy, _cluster(cluster_source="UI")).compliant is False


def test_resource_type_mismatch_yields_no_finding():
    policy = deny("job-policy", "job", leaf("name", "exists"))
    assert evaluate_resource(policy, _cluster()) is None
