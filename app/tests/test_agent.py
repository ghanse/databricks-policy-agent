"""Tests for the Genie Code agent's prompt building, applicability registry, and apply paths."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from policy_agent.policy.model import EnforcementLevel, ResourceType
from policy_agent.remediation.model import RemediationItem, RemediationStatus

from policy_agent_app.backend import agent


def _item(resource_type: ResourceType = ResourceType.CLUSTER) -> RemediationItem:
    return RemediationItem(
        remediation_id="r1",
        policy_name="sp-owned",
        resource_type=resource_type,
        resource_id="c1",
        resource_name="analytics",
        enforcement_level=EnforcementLevel.HARD,
        status=RemediationStatus.OPEN,
        scan_id="scan-1",
        opened_at=None,  # type: ignore[arg-type]
        updated_at=None,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# check_applicability
# ---------------------------------------------------------------------------


def test_cluster_not_applicable():
    applicable, reason = agent.check_applicability("cluster", {"num_workers": 2})
    assert applicable is False
    assert "cluster changes cannot be applied" in reason
    assert "on-behalf-of" in reason
    assert "manually" in reason


def test_job_not_applicable():
    applicable, reason = agent.check_applicability("job", {"tags": {"env": "prod"}})
    assert applicable is False


def test_sql_warehouse_not_applicable():
    applicable, reason = agent.check_applicability("sql_warehouse", {"cluster_size": "Small"})
    assert applicable is False


def test_serving_endpoint_tags_applicable():
    applicable, reason = agent.check_applicability("serving_endpoint", {"tags": {"team": "ai"}})
    assert applicable is True
    assert reason == ""


def test_serving_endpoint_non_tag_field_not_applicable():
    applicable, reason = agent.check_applicability("serving_endpoint", {"owner": "sp@company.com"})
    assert applicable is False
    assert "serving endpoint changes cannot be applied" in reason
    assert "tags" in reason


def test_app_description_applicable():
    applicable, reason = agent.check_applicability("app", {"description": "Owned by team X"})
    assert applicable is True


def test_app_compute_size_applicable():
    applicable, reason = agent.check_applicability("app", {"compute_size": "SMALL"})
    assert applicable is True


def test_app_name_not_applicable():
    applicable, reason = agent.check_applicability("app", {"name": "prod-policy-agent"})
    assert applicable is False
    assert "app changes cannot be applied" in reason
    assert "name" in reason


def test_app_owner_not_applicable():
    applicable, reason = agent.check_applicability("app", {"owner": "sp@company.com"})
    assert applicable is False


def test_app_mixed_some_bad_not_applicable():
    # Even one un-writable field makes the whole proposal not applicable.
    applicable, reason = agent.check_applicability(
        "app", {"description": "ok", "source_code_path": "/evil"}
    )
    assert applicable is False
    assert "app changes cannot be applied" in reason
    assert "source_code_path" in reason


def test_empty_changes_not_applicable():
    applicable, reason = agent.check_applicability("app", {})
    assert applicable is False


# ---------------------------------------------------------------------------
# propose_change sets applicable on the returned proposal
# ---------------------------------------------------------------------------


def test_propose_change_marks_cluster_not_applicable():
    canned = '{"summary": "Add tags.", "diff": "+ tags: env: prod", "changes": {"tags": {"env": "prod"}}}'
    proposal = agent.propose_change(
        _item(ResourceType.CLUSTER), "", "", complete=lambda _e, _s, _u: canned
    )
    assert proposal.applicable is False
    assert "cluster changes cannot be applied" in proposal.not_applicable_reason
    assert "manually" in proposal.not_applicable_reason


def test_propose_change_marks_serving_endpoint_tags_applicable():
    canned = '{"summary": "Tag it.", "diff": "+ tags: team: ai", "changes": {"tags": {"team": "ai"}}}'
    proposal = agent.propose_change(
        _item(ResourceType.SERVING_ENDPOINT), "", "", complete=lambda _e, _s, _u: canned
    )
    assert proposal.applicable is True
    assert proposal.not_applicable_reason == ""


def test_propose_change_marks_app_name_not_applicable():
    canned = '{"summary": "Rename.", "diff": "- name: x\\n+ name: prod-x", "changes": {"name": "prod-x"}}'
    proposal = agent.propose_change(
        _item(ResourceType.APP), "", "", complete=lambda _e, _s, _u: canned
    )
    assert proposal.applicable is False
    assert "app changes cannot be applied" in proposal.not_applicable_reason
    assert "name" in proposal.not_applicable_reason


# ---------------------------------------------------------------------------
# to_dict / from_dict round-trips applicable fields
# ---------------------------------------------------------------------------


def test_proposal_applicable_roundtrips():
    p = agent.AgentProposal(
        proposal_id="p1",
        summary="ok",
        diff="",
        changes={"tags": {"k": "v"}},
        applicable=True,
        not_applicable_reason="",
    )
    assert agent.AgentProposal.from_dict(p.to_dict()).applicable is True


def test_proposal_not_applicable_roundtrips():
    p = agent.AgentProposal(
        proposal_id="p2",
        summary="bad",
        diff="",
        changes={"owner": "x"},
        applicable=False,
        not_applicable_reason="owner field not writable",
    )
    recovered = agent.AgentProposal.from_dict(p.to_dict())
    assert recovered.applicable is False
    assert recovered.not_applicable_reason == "owner field not writable"


# ---------------------------------------------------------------------------
# apply_change (write path, assumes check_applicability already passed)
# ---------------------------------------------------------------------------


def test_apply_change_patches_serving_endpoint_tags():
    calls = {}

    def patch(name, add_tags):
        calls["name"] = name
        calls["tags"] = {t.key: t.value for t in add_tags}

    workspace_client = SimpleNamespace(serving_endpoints=SimpleNamespace(patch=patch))
    item = replace(_item(), resource_type=ResourceType.SERVING_ENDPOINT, resource_id="my-endpoint")
    proposal = agent.AgentProposal(
        proposal_id="p1",
        summary="Tag it",
        diff="",
        changes={"tags": {"managed_by": "policy-agent"}},
        applicable=True,
    )
    applied, message = agent.apply_change(workspace_client, item, proposal)
    assert applied is True
    assert calls == {"name": "my-endpoint", "tags": {"managed_by": "policy-agent"}}


def test_apply_change_updates_app_description_only():
    calls = {}

    def update(name, app):
        calls["name"] = name
        calls["description"] = app.description
        calls["compute_size"] = getattr(app, "compute_size", None)

    workspace_client = SimpleNamespace(apps=SimpleNamespace(update=update))
    item = replace(_item(), resource_type=ResourceType.APP, resource_id="my-app")
    # source_code_path is not in WRITABLE_FIELDS["app"] and must be silently dropped.
    proposal = agent.AgentProposal(
        proposal_id="p1",
        summary="Describe it",
        diff="",
        changes={"description": "Platform team app", "source_code_path": "/evil"},
        applicable=True,
    )
    applied, message = agent.apply_change(workspace_client, item, proposal)
    assert applied is True
    assert calls["name"] == "my-app"
    assert calls["description"] == "Platform team app"


def test_apply_change_no_changes_returns_false():
    proposal = agent.AgentProposal(
        proposal_id="p1", summary="x", diff="", changes={}, applicable=False
    )
    applied, message = agent.apply_change(SimpleNamespace(), _item(), proposal)
    assert applied is False


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def test_build_prompt_includes_finding_and_recommended_action():
    prompt = agent.build_prompt(_item(), "Reassign owner.", "Owned by a user.")
    assert "sp-owned" in prompt
    assert "Reassign owner." in prompt
    assert "Owned by a user." in prompt


def test_propose_change_parses_json_response():
    canned = (
        '{"summary": "Reassign to a service principal.", '
        '"diff": "- owner_type: user\\n+ owner_type: service_principal", '
        '"changes": {"owner_type": "service_principal"}}'
    )
    proposal = agent.propose_change(
        _item(), "Reassign owner.", "Owned by a user.", complete=lambda _e, _s, _u: canned
    )
    assert proposal.summary == "Reassign to a service principal."
    assert "service_principal" in proposal.diff
    assert proposal.changes == {"owner_type": "service_principal"}
    assert proposal.proposal_id
    # cluster is not in WRITABLE_FIELDS, so this is not applicable
    assert proposal.applicable is False


def test_propose_change_tolerates_fenced_and_prose_wrapped_json():
    canned = 'Sure!\n```json\n{"summary": "Fix it", "diff": "+ x: 1", "changes": {"x": 1}}\n```'
    proposal = agent.propose_change(_item(), "", "", complete=lambda _e, _s, _u: canned)
    assert proposal.summary == "Fix it"
    assert proposal.changes == {"x": 1}


def test_propose_change_falls_back_to_raw_text_when_not_json():
    proposal = agent.propose_change(_item(), "", "", complete=lambda _e, _s, _u: "just some text")
    assert proposal.diff == "just some text"
    assert proposal.changes == {}
    assert proposal.applicable is False
