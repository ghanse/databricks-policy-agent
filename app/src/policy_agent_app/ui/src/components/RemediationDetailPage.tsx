import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AgentProposal, RemediationDetail, RemediationEvent } from "../types";
import { enforcementLabel, eventTypeLabel, resourceTypeLabel, statusLabel } from "../labels";
import { useToast } from "../toast";
import { highlightDiff } from "../highlight";
import { resourceUrl } from "../resourceUrl";
import { AssigneeTypeahead } from "./AssigneeTypeahead";
import {
  AssignIcon,
  ChatIcon,
  CheckIcon,
  ClockIcon,
  ExternalIcon,
  LightbulbIcon,
  SparkleIcon,
  XIcon,
} from "./icons";

/** Returns the latest pending AgentProposal from the audit trail, or null if the most
 *  recent proposal has already been accepted or rejected. */
function _latestPendingProposal(events: RemediationEvent[]): AgentProposal | null {
  // Walk backwards: find the last agent_proposed; if an accept/reject comes after it, it's resolved.
  let lastProposedIdx = -1;
  for (let i = events.length - 1; i >= 0; i--) {
    const t = events[i].event_type;
    if (t === "agent_accepted" || t === "agent_rejected") return null;
    if (t === "agent_proposed") { lastProposedIdx = i; break; }
  }
  if (lastProposedIdx === -1) return null;
  try {
    const payload = JSON.parse(events[lastProposedIdx].payload || "{}");
    if (!payload.proposal_id) return null;
    return {
      proposal_id: payload.proposal_id,
      summary: payload.summary ?? "",
      diff: payload.diff ?? "",
      changes: payload.changes ?? {},
      endpoint: payload.endpoint ?? "",
      applicable: payload.applicable ?? false,
      not_applicable_reason: payload.not_applicable_reason ?? "",
    };
  } catch {
    return null;
  }
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

/** Full-page view of one remediation item: when it was opened, assigned, and resolved, its
 *  recommended action, the assignment controls, the Genie Code workflow, and the full audit
 *  trail of status changes and comments. */
export function RemediationDetailPage({
  remediationId,
  workspaceUrl,
  onBack,
  onChanged,
  autoPropose = false,
}: {
  remediationId: string;
  workspaceUrl: string;
  onBack: () => void;
  onChanged: () => void;
  /** Kick off a Genie Code proposal on load (used when opened via the table's action). */
  autoPropose?: boolean;
}) {
  const [item, setItem] = useState<RemediationDetail | null>(null);
  const [error, setError] = useState("");
  const [assignee, setAssignee] = useState("");
  const [commentText, setCommentText] = useState("");
  const [proposal, setProposal] = useState<AgentProposal | null>(null);
  const [thinking, setThinking] = useState(false);
  const toast = useToast();

  const load = () =>
    api
      .getRemediation(remediationId)
      .then((detail) => {
        setItem(detail);
        setAssignee(detail.assignee ?? "");
        // Restore the latest pending Genie Code proposal from the audit trail so it
        // survives page navigations. A proposal is "pending" when no agent_accepted or
        // agent_rejected event follows the last agent_proposed event.
        const restored = _latestPendingProposal(detail.events);
        if (restored) setProposal(restored);
      })
      .catch((e) => setError(String(e)));
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remediationId]);

  // When opened via the table's "Assign to Genie Code" action, start the proposal once the
  // item has loaded and is still open.
  const autoProposed = useRef(false);
  useEffect(() => {
    const open = item?.status === "open" || item?.status === "in_progress";
    if (autoPropose && item && open && !autoProposed.current && !proposal && !thinking) {
      autoProposed.current = true;
      proposeAgentChange();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoPropose, item]);

  const act = async (action: string, note: string, who?: string) => {
    try {
      await api.remediationAction(remediationId, action, note, who);
      await load();
      onChanged();
      return true;
    } catch (e) {
      toast.push(String(e), "error");
      return false;
    }
  };

  const saveAssignee = async () => {
    if (!assignee.trim()) return;
    if (await act("assign", "", assignee.trim())) {
      toast.push(
        <>
          Assigned to <strong>{assignee.trim()}</strong>.
        </>,
        "save",
      );
    }
  };

  const addComment = async () => {
    const text = commentText.trim();
    if (!text) return;
    if (await act("comment", text)) {
      setCommentText("");
      toast.push("Comment added to the audit trail.", "save");
    }
  };

  const proposeAgentChange = async () => {
    setThinking(true);
    setProposal(null);
    try {
      const result = await api.agentPropose(remediationId);
      setProposal(result);
      await load();
      toast.push("Genie Code proposed a change — review the diff below.", "save");
    } catch (e) {
      toast.push(String(e), "error");
    } finally {
      setThinking(false);
    }
  };

  const decideAgent = async (accept: boolean) => {
    if (!proposal) return;
    try {
      if (accept) {
        const result = await api.agentAccept(remediationId, proposal.proposal_id);
        toast.push(result.message || "Genie Code change accepted.", "save");
      } else {
        await api.agentReject(remediationId, proposal.proposal_id);
        toast.push("Genie Code change rejected.", "delete");
      }
      setProposal(null);
      await load();
      onChanged();
    } catch (e) {
      toast.push(String(e), "error");
    }
  };

  if (error) {
    return (
      <>
        <div className="crumbs">
          <button onClick={onBack}>Remediations</button>
          <span className="sep">/</span>
          <span className="here">{remediationId.slice(0, 8)}</span>
        </div>
        <div className="panel">
          <div className="error">{error}</div>
        </div>
      </>
    );
  }
  if (!item) {
    return (
      <div className="panel">
        <div className="loading">Loading…</div>
      </div>
    );
  }

  const url = resourceUrl(workspaceUrl, item.resource_type, item.resource_id);
  const active = item.status === "open" || item.status === "in_progress";

  return (
    <>
      <div className="crumbs">
        <button onClick={onBack}>Remediations</button>
        <span className="sep">/</span>
        <span className="here">{item.policy_name}</span>
      </div>

      <div className="panel">
        <div className="spread" style={{ marginBottom: 16 }}>
          <div>
            <h2 style={{ fontSize: 19 }}>{item.policy_name}</h2>
            <div className="row" style={{ gap: 8, marginTop: 6 }}>
              <span className={`badge ${item.enforcement_level}`}>
                {enforcementLabel(item.enforcement_level)}
              </span>
              <span className={`badge ${item.status}`}>{statusLabel(item.status)}</span>
              <span className="badge neutral">{resourceTypeLabel(item.resource_type)}</span>
            </div>
          </div>
        </div>

        <div className="form-grid">
          <ReadField
            label="Resource"
            node={
              url ? (
                <a className="reslink" href={url} target="_blank" rel="noreferrer">
                  {item.resource_name} <ExternalIcon size={12} />
                </a>
              ) : (
                <strong>{item.resource_name}</strong>
              )
            }
          />
          <ReadField label="Owner" node={item.assignee || <span className="faint">Unassigned</span>} />
          <ReadField label="Opened" node={fmt(item.opened_at)} />
          <ReadField label="Last updated" node={fmt(item.updated_at)} />
        </div>

        <div style={{ marginTop: 14 }}>
          <label className="field">Recommended action</label>
          {item.recommended_action ? (
            <div className="reco">
              <LightbulbIcon className="ico" size={15} />
              <span>{item.recommended_action}</span>
            </div>
          ) : (
            <span className="faint">—</span>
          )}
        </div>
        {item.finding?.message && (
          <div style={{ marginTop: 14 }}>
            <label className="field">Violation</label>
            <div className="readtext">{item.finding.message}</div>
          </div>
        )}

        {active && (
          <div style={{ marginTop: 18 }}>
            <label className="field">Assign this remediation</label>
            <div className="assign-row">
              <div className="assign-user">
                <AssigneeTypeahead value={assignee} onChange={setAssignee} />
                <button className="action act-neutral" onClick={saveAssignee} disabled={!assignee.trim()}>
                  <AssignIcon size={14} /> Assign
                </button>
              </div>
              <span className="assign-or">or</span>
              <button className="action act-genie" onClick={proposeAgentChange} disabled={thinking}>
                <SparkleIcon size={14} /> {thinking ? "Asking Genie Code…" : "Assign to Genie Code"}
              </button>
            </div>
          </div>
        )}

        {active && (
          <div className="row wrap" style={{ marginTop: 16, gap: 8 }}>
            <button
              className="action act-ok"
              onClick={() =>
                act("resolve", "").then((ok) => ok && toast.push("Marked resolved.", "save"))
              }
            >
              <CheckIcon size={14} /> Resolve
            </button>
            <button
              className="action act-danger"
              onClick={() =>
                act("waive", "").then((ok) => ok && toast.push("Waived.", "delete"))
              }
            >
              <XIcon size={14} /> Waive
            </button>
          </div>
        )}
      </div>

      {active && (thinking || proposal) && (
        <div className="panel">
          <h3>
            <SparkleIcon className="ico" size={16} /> Genie Code
            <span className="hint">Proposed configuration change</span>
          </h3>
          {thinking && !proposal && (
            <div className="readtext">
              Genie Code is drafting the smallest change that resolves this violation…
            </div>
          )}
          {proposal && (
            <div className="agent-proposal">
              <div className="agent-summary">
                <SparkleIcon className="ico" size={15} />
                <span>{proposal.summary}</span>
              </div>
              <label className="field" style={{ marginTop: 12 }}>
                Proposed configuration change
              </label>
              <pre className="code diff">{highlightDiff(proposal.diff || "(no diff returned)")}</pre>
              {!proposal.applicable && (
                <div className="agent-not-applicable">
                  <strong>Note:</strong> {proposal.not_applicable_reason}
                </div>
              )}
              <div className="row" style={{ marginTop: 12, gap: 8 }}>
                <button
                  className="action act-ok"
                  onClick={() => decideAgent(true)}
                  disabled={!proposal.applicable}
                  title={!proposal.applicable ? proposal.not_applicable_reason : undefined}
                >
                  <CheckIcon size={14} /> Accept &amp; apply
                </button>
                <button className="action act-danger" onClick={() => decideAgent(false)}>
                  <XIcon size={14} /> Reject
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="panel">
        <h3>
          Audit trail
          <span className="hint">{item.events.length} events</span>
        </h3>

        <div className="comment-box">
          <ChatIcon className="ico" size={15} />
          <input
            placeholder="Add a comment…"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addComment()}
          />
          <button className="action act-neutral" onClick={addComment} disabled={!commentText.trim()}>
            Comment
          </button>
        </div>

        {item.events.length === 0 ? (
          <div className="empty">No activity recorded yet.</div>
        ) : (
          <ol className="timeline">
            {item.events.map((event) => (
              <li key={event.event_id} className={`timeline-item ev-${event.event_type}`}>
                <span className="timeline-dot">
                  <ClockIcon size={12} />
                </span>
                <div className="timeline-body">
                  <div className="timeline-head">
                    <strong>{eventTypeLabel(event.event_type)}</strong>
                    {event.from_status && event.to_status && (
                      <span className="faint">
                        {" "}
                        {statusLabel(event.from_status)} → {statusLabel(event.to_status)}
                      </span>
                    )}
                    <span className="timeline-when">{fmt(event.created_at)}</span>
                  </div>
                  <div className="timeline-meta">
                    by <span className="mono">{event.actor}</span>
                  </div>
                  {event.note && <div className="timeline-note">{event.note}</div>}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </>
  );
}

function ReadField({ label, node }: { label: string; node: React.ReactNode }) {
  return (
    <div>
      <label className="field">{label}</label>
      <div className="readval">{node}</div>
    </div>
  );
}
