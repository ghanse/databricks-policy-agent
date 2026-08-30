import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Policy } from "../types";
import { resourceTypeLabel, statusLabel } from "../labels";
import { NoteDialog, type NoteRequest } from "./NoteDialog";
import { FilterBar } from "./FilterBar";

const ACTIONS: Record<string, string[]> = {
  draft: ["submit"],
  rejected: ["submit"],
  in_review: ["approve", "reject"],
  approved: ["archive"],
};

// A short, plain-language read on where each policy sits in the workflow.
const NEXT_STEP: Record<string, string> = {
  draft: "Waiting to be submitted for review.",
  rejected: "Was sent back — edit and resubmit.",
  in_review: "Awaiting an approver's decision.",
  approved: "Live — evaluated on every scan.",
  archived: "Retired; no longer scanned.",
};

export function ApprovalsTab() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState<NoteRequest | null>(null);
  const [search, setSearch] = useState("");
  const [fStatus, setFStatus] = useState("");

  const refresh = () => api.listPolicies().then(setPolicies).catch((e) => setError(String(e)));
  useEffect(() => {
    refresh();
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return policies.filter(
      (p) => (!q || p.policy.toLowerCase().includes(q)) && (!fStatus || p.status === fStatus),
    );
  }, [policies, search, fStatus]);

  const promptAction = (name: string, action: string) => {
    setError("");
    setDialog({
      title: `${action[0].toUpperCase()}${action.slice(1)} — ${name}`,
      description: "This is recorded as an immutable approval event.",
      confirmLabel: action[0].toUpperCase() + action.slice(1),
      onConfirm: async (note) => {
        try {
          await api.transition(name, action, note);
          refresh();
        } catch (e) {
          setError(String(e));
        }
      },
    });
  };

  return (
    <div className="panel">
      <h3>Approval workflow</h3>
      {error && <div className="error">{error}</div>}
      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Search policies…"
        filters={[
          {
            label: "Status",
            value: fStatus,
            onChange: setFStatus,
            options: ["draft", "in_review", "approved", "rejected", "archived"].map((s) => ({
              value: s,
              label: statusLabel(s),
            })),
          },
        ]}
      />
      {policies.length === 0 ? (
        <div className="empty">No policies yet. Author one on the Policies tab.</div>
      ) : filtered.length === 0 ? (
        <div className="empty">No matching policies.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Policy</th>
              <th>Type</th>
              <th>Status</th>
              <th>Where it stands</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.policy}>
                <td className="cell-strong">{p.policy}</td>
                <td className="muted">{resourceTypeLabel(p.resource_type)}</td>
                <td>
                  <span className={`badge ${p.status}`}>{statusLabel(p.status)}</span>
                </td>
                <td className="muted">{NEXT_STEP[p.status] ?? ""}</td>
                <td>
                  <div className="row">
                    {(ACTIONS[p.status] ?? []).map((action) => (
                      <button
                        key={action}
                        className="action secondary tiny"
                        onClick={() => promptAction(p.policy, action)}
                      >
                        {action}
                      </button>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <NoteDialog request={dialog} onClose={() => setDialog(null)} />
    </div>
  );
}
