import dataclasses

import pytest
from policy_agent.policy import allow, deny, leaf
from policy_agent.policy.model import PolicyStatus
from policy_agent.scan.engine import run_scan
from policy_agent.storage.backend import save_policy, write_scan

from policy_agent_mcp import tools


def _save(context, policy, *, status=PolicyStatus.APPROVED):
    save_policy(
        context.executor, context.config.storage, dataclasses.replace(policy, status=status)
    )


def test_list_resource_types_reports_capabilities():
    by_type = {entry["resource_type"]: entry for entry in tools.list_resource_types()}
    # A compute type is scannable and taggable and advertises its attributes.
    assert by_type["job"]["scannable"] is True
    assert by_type["job"]["taggable"] is True
    assert "has_retry_policy" in by_type["job"]["attributes"]
    # Quality monitors are enforce-only (no list API); secret scopes are not taggable.
    assert by_type["quality_monitor"]["scannable"] is False
    assert by_type["secret_scope"]["taggable"] is False


def test_describe_resource_type_round_trips_and_rejects_unknown():
    assert tools.describe_resource_type("cluster")["resource_type"] == "cluster"
    with pytest.raises(ValueError, match="Unknown resource type"):
        tools.describe_resource_type("notebook")


def test_list_operators_includes_known_operators():
    operators = tools.list_operators()
    assert "equals" in operators and "matches_regex" in operators
    assert operators == sorted(operators)


def test_list_policies_defaults_to_approved(context):
    _save(context, allow("approved-one", "job", leaf("name", "exists")))
    _save(context, allow("draft-one", "job", leaf("name", "exists")), status=PolicyStatus.DRAFT)

    approved = tools.list_policies(context)
    assert [p["policy"] for p in approved] == ["approved-one"]

    everything = {p["policy"] for p in tools.list_policies(context, status="all")}
    assert everything == {"approved-one", "draft-one"}


def test_list_policies_rejects_unknown_status(context):
    with pytest.raises(ValueError, match="Unknown policy status"):
        tools.list_policies(context, status="bogus")


def test_get_policy_returns_one_and_raises_when_missing(context):
    _save(context, allow("only", "job", leaf("name", "exists")))
    assert tools.get_policy(context, "only")["policy"] == "only"
    with pytest.raises(ValueError, match="No policy named"):
        tools.get_policy(context, "missing")


def test_run_compliance_scan_evaluates_approved_policies(context):
    # A user-owned cluster violates a "must be service-principal owned" deny policy.
    _save(
        context,
        deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal")),
    )
    result = tools.run_compliance_scan(context, resource_types=["cluster"])
    assert result["summary"]["evaluated"] == 1
    assert result["summary"]["violations"] == 1
    assert {v["resource_id"] for v in result["violations"]} == {"c1"}


def test_run_compliance_scan_respects_policy_name_filter(context):
    _save(
        context, deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    )
    # Filtering to a non-existent policy name evaluates nothing.
    result = tools.run_compliance_scan(context, policy_names=["does-not-exist"])
    assert result["summary"]["evaluated"] == 0
    assert result["violations"] == []


def test_recent_scans_and_findings_round_trip(context):
    policy = deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    result = run_scan(context.workspace_client, [policy], None)
    write_scan(context.executor, context.config.storage, result, triggered_by="mcp:test")

    scans = tools.list_recent_scans(context, limit=5)
    assert len(scans) == 1
    assert scans[0]["scan_id"] == result.scan_id

    findings = tools.get_scan_findings(context, result.scan_id)
    assert {f["resource_id"] for f in findings} == {"c1"}
