"""Remediation cycle endpoints: list, detail, audit trail, actions, and Genie Code."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.remediation.cycle import advance, assign, comment, make_event, resolve, waive
from policy_agent.remediation.model import (
    RemediationEvent,
    RemediationEventType,
    RemediationItem,
)
from policy_agent.scan.results import Finding
from policy_agent.storage.backend import (
    SqlExecutor,
    load_policies,
    read_findings,
    read_remediation_events,
    read_remediations,
    save_remediation,
    save_remediation_event,
)

from policy_agent_app.backend import agent
from policy_agent_app.backend.auth import current_user, require_runner
from policy_agent_app.backend.dependencies import (
    get_config,
    get_effective_config,
    get_executor,
    get_user_workspace_client,
    get_workspace_client,
)
from policy_agent_app.backend.lookups import find_remediation
from policy_agent_app.backend.schemas import (
    AgentDecisionRequest,
    RemediationActionRequest,
    finding_to_dict,
    remediation_event_to_dict,
    remediation_to_dict,
)

router = APIRouter(prefix="/remediations", tags=["remediations"])

# The audit event each manual action records. The status change itself comes from the
# library cycle function the action calls.
_ACTION_EVENTS = {
    "advance": RemediationEventType.ADVANCED,
    "resolve": RemediationEventType.RESOLVED,
    "waive": RemediationEventType.WAIVED,
    "assign": RemediationEventType.ASSIGNED,
    "comment": RemediationEventType.COMMENTED,
}


@router.get("")
def list_remediations(
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> list[dict[str, Any]]:
    """List remediation items, most recently opened first."""
    return [remediation_to_dict(item) for item in read_remediations(executor, config.storage)]


@router.get("/{remediation_id}")
def get_remediation(
    remediation_id: str,
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_config),
    _user: str = Depends(current_user),
) -> dict[str, Any]:
    """Return one remediation item with its recommended action and full audit trail."""
    item = find_remediation(executor, config, remediation_id)
    finding = _finding_for(executor, config, item)
    events = read_remediation_events(executor, config.storage, remediation_id)
    return {
        **remediation_to_dict(item),
        "recommended_action": _recommended_action(executor, config, item, finding),
        "finding": finding_to_dict(finding) if finding is not None else None,
        "events": [remediation_event_to_dict(event) for event in events],
    }


@router.post("/{remediation_id}/action")
def act_on_remediation(
    remediation_id: str,
    body: RemediationActionRequest,
    user: str = Depends(current_user),
    _roles: set[Role] = Depends(require_runner),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_effective_config),
) -> dict[str, Any]:
    """Advance, resolve, waive, assign, or comment on a remediation item."""
    item = find_remediation(executor, config, remediation_id)
    updated, events = _apply_action(item, body, user)
    save_remediation(executor, config.storage, updated)
    for event in events:
        save_remediation_event(executor, config.storage, event)
    return remediation_to_dict(updated)


@router.post("/{remediation_id}/agent/propose")
def propose_agent_change(
    remediation_id: str,
    _roles: set[Role] = Depends(require_runner),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_effective_config),
    workspace_client=Depends(get_workspace_client),
) -> dict[str, Any]:
    """Ask Genie Code to propose a fix for the item and record it on the audit trail."""
    item = find_remediation(executor, config, remediation_id)
    finding = _finding_for(executor, config, item)
    try:
        proposal = agent.propose_change(
            item,
            _recommended_action(executor, config, item, finding),
            finding.message if finding is not None else "",
            complete=agent.make_completer(workspace_client),
        )
    except Exception as exc:  # noqa: BLE001 - surface the endpoint error to the caller
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Genie Code could not produce a proposal: {exc}",
        ) from exc
    now = datetime.now(UTC)
    save_remediation_event(
        executor,
        config.storage,
        make_event(
            remediation_id,
            RemediationEventType.AGENT_PROPOSED,
            "genie-code",
            now,
            note=proposal.summary,
            payload=json.dumps(proposal.to_dict()),
        ),
    )
    return proposal.to_dict()


@router.post("/{remediation_id}/agent/accept")
def accept_agent_change(
    remediation_id: str,
    body: AgentDecisionRequest,
    user: str = Depends(current_user),
    _roles: set[Role] = Depends(require_runner),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_effective_config),
    user_client=Depends(get_user_workspace_client),
) -> dict[str, Any]:
    """Accept a Genie Code proposal: submit the change and move the item in progress.

    The change is applied on-behalf-of the accepting user, so it uses their permissions and
    is attributed to them, within the app's granted scopes. Returns 400 when the proposal's
    changes are not applicable (the UI should have frozen the button, but the backend also
    guards so the API stays honest).
    """
    item = find_remediation(executor, config, remediation_id)
    proposal = _find_proposal(executor, config, remediation_id, body.proposal_id)
    applicable, reason = agent.check_applicability(item.resource_type.value, proposal.changes)
    if not applicable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot apply this change automatically: {reason}",
        )
    applied, message = agent.apply_change(user_client, item, proposal)
    now = datetime.now(UTC)
    updated = assign(advance(item, now, note=proposal.summary), "genie-code", now)
    save_remediation(executor, config.storage, updated)
    save_remediation_event(
        executor,
        config.storage,
        make_event(
            remediation_id,
            RemediationEventType.AGENT_ACCEPTED,
            user,
            now,
            note=f"{body.note + ' ' if body.note else ''}{message}".strip(),
            from_status=item.status if item.status != updated.status else None,
            to_status=updated.status if item.status != updated.status else None,
            payload=json.dumps(proposal.to_dict()),
        ),
    )
    return {"applied": applied, "message": message, **remediation_to_dict(updated)}


@router.post("/{remediation_id}/agent/reject")
def reject_agent_change(
    remediation_id: str,
    body: AgentDecisionRequest,
    user: str = Depends(current_user),
    _roles: set[Role] = Depends(require_runner),
    executor: SqlExecutor = Depends(get_executor),
    config: PolicyAgentConfig = Depends(get_effective_config),
) -> dict[str, Any]:
    """Reject a Genie Code proposal, recording it on the audit trail."""
    item = find_remediation(executor, config, remediation_id)
    proposal = _find_proposal(executor, config, remediation_id, body.proposal_id)
    save_remediation_event(
        executor,
        config.storage,
        make_event(
            remediation_id,
            RemediationEventType.AGENT_REJECTED,
            user,
            datetime.now(UTC),
            note=body.note or f"Rejected Genie Code proposal: {proposal.summary}",
            payload=json.dumps(proposal.to_dict()),
        ),
    )
    return remediation_to_dict(item)


def _find_proposal(
    executor: SqlExecutor, config: PolicyAgentConfig, remediation_id: str, proposal_id: str
) -> agent.AgentProposal:
    for event in read_remediation_events(executor, config.storage, remediation_id):
        if event.event_type is RemediationEventType.AGENT_PROPOSED and event.payload:
            try:
                data = json.loads(event.payload)
            except ValueError:
                continue
            if data.get("proposal_id") == proposal_id:
                return agent.AgentProposal.from_dict(data)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Unknown Genie Code proposal {proposal_id!r}.",
    )


def _apply_action(
    item: RemediationItem, body: RemediationActionRequest, actor: str
) -> tuple[RemediationItem, list[RemediationEvent]]:
    now = datetime.now(UTC)
    if body.action not in _ACTION_EVENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown remediation action {body.action!r}.",
        )
    event_type = _ACTION_EVENTS[body.action]
    events: list[RemediationEvent] = []

    if body.action == "advance":
        updated = advance(item, now, body.note)
        events.append(_event(item, updated, event_type, actor, now, body.note))
        if body.assignee:
            assigned = assign(updated, body.assignee, now)
            events.append(_event(updated, assigned, RemediationEventType.ASSIGNED, actor, now,
                                  f"Assigned to {body.assignee}."))
            return assigned, events
        return updated, events

    if body.action == "resolve":
        updated = resolve(item, now, body.note)
        return updated, [_event(item, updated, event_type, actor, now, body.note)]

    if body.action == "waive":
        updated = waive(item, now, body.note)
        return updated, [_event(item, updated, event_type, actor, now, body.note)]

    if body.action == "assign":
        if not body.assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The 'assign' action requires an 'assignee'.",
            )
        updated = assign(item, body.assignee, now)
        return updated, [_event(item, updated, event_type, actor, now,
                                body.note or f"Assigned to {body.assignee}.")]

    # comment: no status change, just a note on the trail.
    updated = comment(item, now, body.note)
    return updated, [_event(item, updated, event_type, actor, now, body.note)]


def _event(
    before: RemediationItem,
    after: RemediationItem,
    event_type: RemediationEventType,
    actor: str,
    now: datetime,
    note: str,
) -> RemediationEvent:
    changed = before.status != after.status
    return make_event(
        after.remediation_id,
        event_type,
        actor,
        now,
        note=note,
        from_status=before.status if changed else None,
        to_status=after.status if changed else None,
    )


def _finding_for(
    executor: SqlExecutor, config: PolicyAgentConfig, item: RemediationItem
) -> Finding | None:
    if not item.scan_id:
        return None
    for finding in read_findings(executor, config.storage, item.scan_id):
        if (
            finding.policy_name == item.policy_name
            and finding.resource_id == item.resource_id
            and not finding.compliant
        ):
            return finding
    return None


def _recommended_action(
    executor: SqlExecutor,
    config: PolicyAgentConfig,
    item: RemediationItem,
    finding: Finding | None,
) -> str:
    if finding is not None and finding.remediation:
        return finding.remediation
    for policy in load_policies(executor, config.storage):
        if policy.name == item.policy_name:
            return policy.remediation
    return ""
