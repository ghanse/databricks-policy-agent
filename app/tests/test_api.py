from policy_agent.approval.roles import Role

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


def test_cannot_approve_a_draft_returns_409(client):
    client.post("/api/v1/policies", json=CLUSTER_POLICY)
    response = client.post("/api/v1/policies/sp-owned/approve", json={})
    assert response.status_code == 409


def test_unknown_policy_returns_404(client):
    assert client.get("/api/v1/policies/missing").status_code == 404


def test_unknown_resource_type_returns_400(client):
    response = client.post("/api/v1/policies", json={**CLUSTER_POLICY, "resource_type": "INVALID"})
    assert response.status_code == 400
