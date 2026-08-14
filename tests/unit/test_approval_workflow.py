import pytest

from policy_agent.approval import Role, approve, archive, reject, resolve_roles, submit_for_review
from policy_agent.approval.roles import can_approve, can_author, can_run_scans
from policy_agent.errors import AuthorizationError, WorkflowError
from policy_agent.policy import deny, leaf
from policy_agent.policy.model import PolicyStatus

AUTHOR = {Role.POLICY_AUTHOR}
APPROVER = {Role.POLICY_APPROVER}
ADMIN = {Role.ADMIN}


def _draft():
    return deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))


def test_resolve_roles_unions_group_grants():
    mappings = {"authors": [Role.POLICY_AUTHOR], "leads": [Role.POLICY_APPROVER, Role.ADMIN]}
    assert resolve_roles(["authors", "leads"], mappings) == {
        Role.POLICY_AUTHOR,
        Role.POLICY_APPROVER,
        Role.ADMIN,
    }
    assert resolve_roles(["unmapped"], mappings) == set()


def test_admin_can_author_approve_and_run():
    assert can_author(ADMIN) and can_approve(ADMIN) and can_run_scans(ADMIN)


def test_full_happy_path_draft_to_approved():
    policy = _draft()
    in_review, submit_event = submit_for_review(policy, "alice@example.com", AUTHOR)
    assert in_review.status is PolicyStatus.IN_REVIEW
    assert submit_event.from_status is PolicyStatus.DRAFT
    assert submit_event.to_status is PolicyStatus.IN_REVIEW

    approved, approve_event = approve(in_review, "bob@example.com", APPROVER)
    assert approved.status is PolicyStatus.APPROVED
    assert approved.version == policy.version + 1
    assert approve_event.actor == "bob@example.com"


def test_submit_requires_author_role():
    with pytest.raises(AuthorizationError):
        submit_for_review(_draft(), "eve@example.com", {Role.VIEWER})


def test_approve_requires_approver_role():
    in_review, _ = submit_for_review(_draft(), "alice@example.com", AUTHOR)
    with pytest.raises(AuthorizationError):
        approve(in_review, "alice@example.com", AUTHOR)


def test_approver_may_not_approve_own_submission():
    in_review, _ = submit_for_review(_draft(), "alice@example.com", AUTHOR | APPROVER)
    with pytest.raises(AuthorizationError):
        approve(in_review, "alice@example.com", APPROVER, author="alice@example.com")


def test_cannot_approve_a_draft():
    with pytest.raises(WorkflowError):
        approve(_draft(), "bob@example.com", APPROVER)


def test_reject_returns_to_rejected_and_can_resubmit():
    in_review, _ = submit_for_review(_draft(), "alice@example.com", AUTHOR)
    rejected, _ = reject(in_review, "bob@example.com", APPROVER, note="needs scope")
    assert rejected.status is PolicyStatus.REJECTED
    resubmitted, _ = submit_for_review(rejected, "alice@example.com", AUTHOR)
    assert resubmitted.status is PolicyStatus.IN_REVIEW


def test_archive_requires_admin():
    with pytest.raises(AuthorizationError):
        archive(_draft(), "bob@example.com", APPROVER)
    archived, event = archive(_draft(), "root@example.com", ADMIN)
    assert archived.status is PolicyStatus.ARCHIVED
    assert event.to_status is PolicyStatus.ARCHIVED
