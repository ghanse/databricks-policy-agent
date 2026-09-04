"""Genie Code agent: propose and apply a resource fix for a remediation item.

"Assign to Genie Code" asks a Databricks model-serving endpoint to draft the smallest
configuration change that resolves a violation, using the scan finding and the policy's
recommended action as the prompt. The model answers with a one-line summary and a YAML diff
of the resource configuration; the user then accepts or rejects it. On acceptance the change
is submitted to the workspace directly.

The model call is isolated behind an injectable ``complete`` callable so the routes stay
thin and the behaviour is unit-testable without a live endpoint.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from policy_agent.remediation.model import RemediationItem

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

ENV_AGENT_ENDPOINT = "POLICY_AGENT_AGENT_ENDPOINT"
DEFAULT_AGENT_ENDPOINT = "databricks-claude-sonnet-4-5"

# A completion function takes (endpoint, system prompt, user prompt) and returns raw text.
CompleteFn = Callable[[str, str, str], str]

_SYSTEM_PROMPT = (
    "You are Genie Code, a Databricks agent that fixes resource misconfigurations. "
    "You are given a policy violation and the recommended action. Propose the smallest "
    "possible change to the resource configuration that resolves the violation. "
    "Reply with a single JSON object and nothing else, shaped as: "
    '{"summary": "<one short sentence>", '
    '"diff": "<a unified-style YAML diff, lines prefixed with + or - >", '
    '"changes": {"<field>": <new value>}}. '
    "Keep the summary to one sentence. The diff must show only the resource configuration "
    "keys that change, as YAML. Do not include any prose outside the JSON."
)

# ---------------------------------------------------------------------------
# Applicability registry
# ---------------------------------------------------------------------------

# Single source of truth: which fields can be changed per resource type when the
# app acts on behalf of the user (OBO).  Only resource types covered by the app's
# declared OBO scopes are present:
#   - ``apps``          → app.description, app.compute_size (apps.update)
#   - ``model-serving`` → serving_endpoint.tags (serving_endpoints.patch)
# Jobs, clusters, and SQL warehouses have no OBO scope, so they are absent.
WRITABLE_FIELDS: dict[str, frozenset[str]] = {
    "app": frozenset({"description", "compute_size"}),
    "serving_endpoint": frozenset({"tags"}),
}


def check_applicability(resource_type: str, changes: dict[str, Any]) -> tuple[bool, str]:
    """Returns whether a proposed change can be applied from the app, and why not if not.

    Args:
        resource_type: The resource type value (e.g. ``"app"``, ``"cluster"``).
        changes: The structured field→value map from a Genie Code proposal.

    Returns:
        ``(True, "")`` when all proposed fields are writable via OBO.
        ``(False, human_readable_reason)`` otherwise.
    """
    if not changes:
        return False, "No structured change was proposed."
    resource_label = resource_type.replace("_", " ")
    writable = WRITABLE_FIELDS.get(resource_type)
    if writable is None:
        return False, (
            f"The recommended {resource_label} changes cannot be applied from the app. "
            "Databricks Apps on-behalf-of auth covers only apps and model serving endpoints — "
            f"{resource_label} resources are out of reach. "
            "Apply this change manually through the workspace UI or admin tools."
        )
    bad = sorted(set(changes) - writable)
    if bad:
        plural = "fields" if len(bad) > 1 else "field"
        supported = sorted(writable)
        return False, (
            f"The recommended {resource_label} changes cannot be applied from the app. "
            f"The {plural} {bad} cannot be modified via the on-behalf-of API "
            f"(only {supported} {'are' if len(supported) > 1 else 'is'} supported). "
            "Apply this change manually."
        )
    return True, ""


# ---------------------------------------------------------------------------
# Proposal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentProposal:
    """A Genie Code proposal for resolving a remediation item.

    Attributes:
        proposal_id: Unique identifier used to accept or reject this proposal.
        summary: One-sentence description of the proposed change.
        diff: A YAML diff of the resource configuration, lines prefixed with ``+``/``-``.
        changes: Structured field-to-new-value map used to apply the change, best effort.
        endpoint: The model-serving endpoint that produced the proposal.
        applicable: Whether the proposed change can be applied from this app via OBO auth.
        not_applicable_reason: Human-readable explanation when ``applicable`` is ``False``.
    """

    proposal_id: str
    summary: str
    diff: str
    changes: dict[str, Any] = field(default_factory=dict)
    endpoint: str = ""
    applicable: bool = False
    not_applicable_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Returns a JSON-serialisable mapping of the proposal."""
        return {
            "proposal_id": self.proposal_id,
            "summary": self.summary,
            "diff": self.diff,
            "changes": self.changes,
            "endpoint": self.endpoint,
            "applicable": self.applicable,
            "not_applicable_reason": self.not_applicable_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentProposal:
        """Rebuilds a proposal from a stored mapping (the audit-event payload)."""
        return cls(
            proposal_id=str(data.get("proposal_id", "")),
            summary=str(data.get("summary", "")),
            diff=str(data.get("diff", "")),
            changes=dict(data.get("changes") or {}),
            endpoint=str(data.get("endpoint", "")),
            applicable=bool(data.get("applicable", False)),
            not_applicable_reason=str(data.get("not_applicable_reason", "")),
        )


# ---------------------------------------------------------------------------
# Core agent functions
# ---------------------------------------------------------------------------


def agent_endpoint() -> str:
    """Returns the model-serving endpoint Genie Code uses, from the environment."""
    return os.environ.get(ENV_AGENT_ENDPOINT, DEFAULT_AGENT_ENDPOINT)


def build_prompt(item: RemediationItem, recommended_action: str, finding_message: str) -> str:
    """Builds the user prompt describing the violation to fix.

    Args:
        item: The remediation item being fixed.
        recommended_action: The policy's remediation guidance.
        finding_message: The scan finding's explanation of the violation.

    Returns:
        The user-message text sent to the model.
    """
    return (
        f"Policy: {item.policy_name}\n"
        f"Resource type: {item.resource_type.value}\n"
        f"Resource name: {item.resource_name}\n"
        f"Resource id: {item.resource_id}\n"
        f"Violation: {finding_message or '(none recorded)'}\n"
        f"Recommended action: {recommended_action or '(none recorded)'}\n\n"
        "Propose the configuration change that resolves this violation."
    )


def propose_change(
    item: RemediationItem,
    recommended_action: str,
    finding_message: str,
    complete: CompleteFn,
    endpoint: str | None = None,
) -> AgentProposal:
    """Asks Genie Code for a proposed fix and parses it into an `AgentProposal`.

    Applicability is checked immediately after parsing: ``proposal.applicable`` tells the
    caller (and the UI) whether the change can be applied from this app via OBO auth, and
    ``proposal.not_applicable_reason`` explains why not when it can't.

    Args:
        item: The remediation item being fixed.
        recommended_action: The policy's remediation guidance.
        finding_message: The scan finding's explanation of the violation.
        complete: Callable that runs the model given ``(endpoint, system, user)``.
        endpoint: Override for the model-serving endpoint; defaults to :func:`agent_endpoint`.

    Returns:
        The parsed proposal, with ``applicable`` and ``not_applicable_reason`` set.
    """
    resolved_endpoint = endpoint or agent_endpoint()
    prompt = build_prompt(item, recommended_action, finding_message)
    raw = complete(resolved_endpoint, _SYSTEM_PROMPT, prompt)
    summary, diff, changes = _parse_response(raw)
    applicable, not_applicable_reason = check_applicability(item.resource_type.value, changes)
    return AgentProposal(
        proposal_id=uuid.uuid4().hex,
        summary=summary,
        diff=diff,
        changes=changes,
        endpoint=resolved_endpoint,
        applicable=applicable,
        not_applicable_reason=not_applicable_reason,
    )


def apply_change(
    workspace_client: WorkspaceClient, item: RemediationItem, proposal: AgentProposal
) -> tuple[bool, str]:
    """Submits an accepted proposal's change to the workspace directly, best effort.

    Args:
        workspace_client: An authenticated Databricks workspace client.
        item: The remediation item being fixed.
        proposal: The accepted proposal.

    Returns:
        A ``(applied, message)`` pair: whether the change was applied and a human-readable
        outcome recorded on the audit trail and shown to the user.
    """
    if not proposal.changes:
        return False, "No structured change was proposed, so nothing was applied automatically."
    try:
        _dispatch_update(
            workspace_client, item.resource_type.value, item.resource_id, proposal.changes
        )
    except Exception as exc:  # noqa: BLE001 - the outcome is surfaced to the user verbatim
        return False, f"Could not apply the change directly: {exc}"
    fields = ", ".join(proposal.changes)
    return True, f"Applied {fields} to {item.resource_name} via the Databricks API."


def make_completer(workspace_client: WorkspaceClient) -> CompleteFn:
    """Builds the default completion function backed by a model-serving endpoint.

    Args:
        workspace_client: An authenticated Databricks workspace client.

    Returns:
        A callable that queries the endpoint and returns the assistant's message text.
    """

    def complete(endpoint: str, system: str, user: str) -> str:
        from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

        response = workspace_client.serving_endpoints.query(
            name=endpoint,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=system),
                ChatMessage(role=ChatMessageRole.USER, content=user),
            ],
            max_tokens=600,
            temperature=0.0,
        )
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        return getattr(message, "content", "") or ""

    return complete


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_response(raw: str) -> tuple[str, str, dict[str, Any]]:
    text = (raw or "").strip()
    payload = _extract_json(text)
    if payload is None:
        return "Genie Code proposed a change.", text, {}
    summary = str(payload.get("summary", "")).strip() or "Genie Code proposed a change."
    diff = str(payload.get("diff", "")).strip()
    changes = payload.get("changes")
    return summary, diff, dict(changes) if isinstance(changes, dict) else {}


def _extract_json(text: str) -> dict[str, Any] | None:
    # Models sometimes wrap JSON in a fenced block; fall back to the first {...} span.
    candidates = [text]
    if "```" in text:
        candidates.append(text.split("```")[1].removeprefix("json").strip())
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _dispatch_update(
    workspace_client: WorkspaceClient, resource_type: str, resource_id: str, changes: dict[str, Any]
) -> None:
    """Apply a proposal's changes to one resource using the caller-supplied client.

    Callers must have already verified applicability via :func:`check_applicability`; this
    function only contains the write paths for OBO-reachable fields.
    """
    if resource_type == "serving_endpoint":
        from databricks.sdk.service.serving import EndpointTag

        tags = [EndpointTag(key=str(k), value=str(v)) for k, v in dict(changes["tags"]).items()]
        workspace_client.serving_endpoints.patch(name=resource_id, add_tags=tags)
        return
    if resource_type == "app":
        from databricks.sdk.service.apps import App

        writable = WRITABLE_FIELDS["app"]
        workspace_client.apps.update(
            name=resource_id,
            app=App(name=resource_id, **{k: v for k, v in changes.items() if k in writable}),
        )
        return
    raise RuntimeError(f"No write path for resource type {resource_type!r}.")
