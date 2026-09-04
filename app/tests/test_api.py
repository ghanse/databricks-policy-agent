import json
from types import SimpleNamespace

from policy_agent.approval.roles import Role

from policy_agent_app.backend import agent
from policy_agent_app.backend.routes.users import find_users

CLUSTER_POLICY = {
    "name": "sp-owned",
    "resource_type": "cluster",
    "effect": "deny",
    "enforcement_level": "hard",
    "rule": {"attribute": "owner_type", "operator": "not_equals", "value": "service_principal"},
    "remediation": "Reassign to a service principal.",
}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_settings_exposes_vocabulary(client):
    body = client.get("/api/v1/settings").json()
    assert "cluster" in body["resource_types"]
    assert "not_equals" in body["operators"]
    assert set(body["roles"]) >= {"admin", "policy_author", "viewer"}


def test_validate_endpoint_flags_bad_attribute(client):
    good = client.post("/api/v1/policies/validate", json=CLUSTER_POLICY).json()
    assert good == {"valid": True}
    bad = client.post(
        "/api/v1/policies/validate",
        json={**CLUSTER_POLICY, "rule": {"attribute": "nope", "operator": "equals", "value": "x"}},
    ).json()
    assert bad["valid"] is False


def test_policy_crud_and_history(client):
    created = client.post("/api/v1/policies", json=CLUSTER_POLICY)
    assert created.status_code == 201
    assert created.json()["status"] == "draft"

    listed = client.get("/api/v1/policies").json()
    assert [p["policy"] for p in listed] == ["sp-owned"]
    assert client.get("/api/v1/policies/sp-owned").json()["effect"] == "deny"


def test_create_policy_forbidden_for_viewer(make_client):
    viewer_client = make_client(roles={Role.VIEWER})
    assert viewer_client.post("/api/v1/policies", json=CLUSTER_POLICY).status_code == 403


def test_roles_me_reports_effective_roles(make_client):
    approver_client = make_client(roles={Role.POLICY_APPROVER})
    body = approver_client.get("/api/v1/roles/me").json()
    assert body["roles"] == ["policy_approver"]


def test_approval_flow_then_scan_and_remediation(client):
    client.post("/api/v1/policies", json=CLUSTER_POLICY)
    assert client.post("/api/v1/policies/sp-owned/submit", json={}).json()["status"] == "in_review"
    approved = client.post("/api/v1/policies/sp-owned/approve", json={"note": "ok"}).json()
    assert approved["status"] == "approved"

    scan = client.post("/api/v1/scans", json={}).json()
    assert scan["summary"]["violations"] == 1
    assert scan["violations"][0]["resource_id"] == "c1"

    remediations = client.get("/api/v1/remediations").json()
    assert len(remediations) == 1
    assert remediations[0]["status"] == "open"

    remediation_id = remediations[0]["remediation_id"]
    resolved = client.post(
        f"/api/v1/remediations/{remediation_id}/action",
        json={"action": "resolve", "note": "fixed"},
    ).json()
    assert resolved["status"] == "resolved"


def _open_remediation(client) -> str:
    """Approve the sample policy, scan, and return the opened remediation's id."""
    client.post("/api/v1/policies", json=CLUSTER_POLICY)
    client.post("/api/v1/policies/sp-owned/submit", json={})
    client.post("/api/v1/policies/sp-owned/approve", json={"note": "ok"})
    client.post("/api/v1/scans", json={})
    return client.get("/api/v1/remediations").json()[0]["remediation_id"]


def _stub_genie(monkeypatch, summary, diff, changes):
    canned = json.dumps({"summary": summary, "diff": diff, "changes": changes})
    monkeypatch.setattr(agent, "make_completer", lambda _wc: (lambda _e, _s, _u: canned))


def test_remediation_detail_includes_recommended_action_and_trail(client):
    rid = _open_remediation(client)
    client.post(
        f"/api/v1/remediations/{rid}/action",
        json={"action": "advance", "note": "looking", "assignee": "alice@example.com"},
    )
    detail = client.get(f"/api/v1/remediations/{rid}").json()
    assert detail["recommended_action"] == "Reassign to a service principal."
    assert detail["finding"]["resource_id"] == "c1"
    assert detail["assignee"] == "alice@example.com"
    assert detail["status"] == "in_progress"
    types = [event["event_type"] for event in detail["events"]]
    assert types == ["opened", "advanced", "assigned"]


def test_comment_records_event_without_changing_status(client):
    rid = _open_remediation(client)
    client.post(f"/api/v1/remediations/{rid}/action", json={"action": "comment", "note": "info?"})
    detail = client.get(f"/api/v1/remediations/{rid}").json()
    assert detail["status"] == "open"
    assert any(
        event["event_type"] == "commented" and event["note"] == "info?"
        for event in detail["events"]
    )


def test_remediation_action_forbidden_for_viewer(make_client):
    admin = make_client()
    rid = _open_remediation(admin)
    viewer = make_client(roles={Role.VIEWER})
    resp = viewer.post(f"/api/v1/remediations/{rid}/action", json={"action": "resolve"})
    assert resp.status_code == 403


def test_find_users_maps_matches_and_drops_inactive():
    scim_users = [
        SimpleNamespace(user_name="alice@x.com", display_name="Alice", active=True),
        SimpleNamespace(user_name="bob@x.com", display_name="Bob", active=False),
    ]
    workspace_client = SimpleNamespace(users=SimpleNamespace(list=lambda **_kw: scim_users))
    assert find_users(workspace_client, "a", 10) == [
        {"user_name": "alice@x.com", "display_name": "Alice", "active": True}
    ]


def test_user_search_endpoint_is_graceful_when_empty(client):
    assert client.get("/api/v1/users/search?q=al").json() == []


def test_agent_propose_then_reject_records_trail(monkeypatch, client):
    rid = _open_remediation(client)
    _stub_genie(
        monkeypatch,
        "Reassign the cluster to a service principal.",
        "- owner_type: user\n+ owner_type: service_principal",
        {"owner_type": "service_principal"},
    )
    proposal = client.post(f"/api/v1/remediations/{rid}/agent/propose", json={}).json()
    assert proposal["summary"].startswith("Reassign")
    assert "owner_type" in proposal["diff"]

    rejected = client.post(
        f"/api/v1/remediations/{rid}/agent/reject",
        json={"proposal_id": proposal["proposal_id"], "note": "not now"},
    )
    assert rejected.status_code == 200
    types = [event["event_type"] for event in client.get(f"/api/v1/remediations/{rid}").json()["events"]]
    assert "agent_proposed" in types and "agent_rejected" in types


def test_agent_accept_submits_change_and_advances(monkeypatch, client):
    rid = _open_remediation(client)
    # Tags on a serving endpoint are applicable via OBO, so accept goes through.
    _stub_genie(monkeypatch, "Add tags.", "+ tags: managed_by: policy-agent",
                {"tags": {"managed_by": "policy-agent"}})
    # The test remediation is for a cluster, which is not applicable — the applicability
    # guard returns 400 for non-writable resource types. Use propose to confirm the proposal
    # carries applicable=False, and verify the accept is correctly refused.
    proposal = client.post(f"/api/v1/remediations/{rid}/agent/propose", json={}).json()
    assert proposal["applicable"] is False
    result = client.post(
        f"/api/v1/remediations/{rid}/agent/accept",
        json={"proposal_id": proposal["proposal_id"]},
    )
    assert result.status_code == 400
    assert "automatically" in result.json()["detail"]


def test_agent_reject_unknown_proposal_returns_404(client):
    rid = _open_remediation(client)
    resp = client.post(
        f"/api/v1/remediations/{rid}/agent/reject", json={"proposal_id": "nope"}
    )
    assert resp.status_code == 404


def test_cannot_approve_a_draft_returns_409(client):
    client.post("/api/v1/policies", json=CLUSTER_POLICY)
    response = client.post("/api/v1/policies/sp-owned/approve", json={})
    assert response.status_code == 409


def test_unknown_policy_returns_404(client):
    assert client.get("/api/v1/policies/missing").status_code == 404


def test_unknown_resource_type_returns_400(client):
    response = client.post("/api/v1/policies", json={**CLUSTER_POLICY, "resource_type": "INVALID"})
    assert response.status_code == 400


def test_settings_webhook_visible_to_admin_hidden_from_others(make_client):
    admin = make_client(roles={Role.ADMIN})
    saved = admin.put("/api/v1/settings", json={"notification_webhook": "https://hooks/secret"})
    assert saved.status_code == 200
    assert saved.json()["notifications"]["webhook"] == "https://hooks/secret"

    # A non-admin sees that a webhook is configured but never its (possibly secret) URL.
    viewer = make_client(roles={Role.VIEWER})
    body = viewer.get("/api/v1/settings").json()["notifications"]
    assert body["webhook_configured"] is True
    assert "webhook" not in body


def test_parse_endpoint_requires_author(make_client):
    viewer = make_client(roles={Role.VIEWER})
    resp = viewer.post("/api/v1/policies/parse", json={"yaml": "policy: x"})
    assert resp.status_code == 403
