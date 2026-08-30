import { useEffect, useState } from "react";
import { api } from "../api";
import type { Policy, Remediation } from "../types";
import { LightbulbIcon } from "./icons";
import { NoteDialog, type NoteRequest } from "./NoteDialog";

const ACTIONS: Record<string, string[]> = {
  open: ["advance", "resolve", "waive"],
  in_progress: ["resolve", "waive"],
};

const ACTION_HELP: Record<string, string> = {
  advance: "Mark this violation as actively being worked on, and optionally assign an owner.",
  resolve: "Record that the underlying violation has been fixed.",
  waive: "Knowingly accept this violation; it stays on the audit trail.",
};

function age(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "1 day";
  if (days < 30) return `${days} days`;
  return `${Math.floor(days / 30)} mo`;
}

export function RemediationsTab() {
  const [items, setItems] = useState<Remediation[]>([]);
  const [reco, setReco] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState<NoteRequest | null>(null);

  const refresh = () => api.listRemediations().then(setItems).catch((e) => setError(String(e)));
  useEffect(() => {
    refresh();
    // Recommended action per remediation comes from the policy's remediation guidance.
    api
      .listPolicies()
      .then((policies: Policy[]) =>
        setReco(Object.fromEntries(policies.map((p) => [p.policy, p.remediation ?? ""]))),
      )
      .catch(() => setReco({}));
  }, []);

  const promptAction = (item: Remediation, action: string) => {
    setError("");
    setDialog({
      title: `${action[0].toUpperCase()}${action.slice(1)} — ${item.policy_name}`,
      description: ACTION_HELP[action],
      confirmLabel: action[0].toUpperCase() + action.slice(1),
      withAssignee: action === "advance",
      onConfirm: async (note, assignee) => {
        try {
          await api.remediationAction(item.remediation_id, action, note, assignee);
          refresh();
        } catch (e) {
          setError(String(e));
        }
      },
    });
  };

  const open = items.filter((i) => i.status === "open" || i.status === "in_progress");

  return (
    <div className="panel">
      <h3>
        Remediation cycle
        <span className="hint">
          {open.length} open · {items.length} total
        </span>
      </h3>
      {error && <div className="error">{error}</div>}
      {items.length === 0 ? (
        <div className="empty">No remediation items yet. Run a scan to open items for any violations.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Policy</th>
              <th>Resource</th>
              <th>Recommended action</th>
              <th>Owner</th>
              <th>Age</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.remediation_id}>
                <td>
                  <span className={`badge ${item.severity}`}>{item.severity}</span>
                </td>
                <td className="cell-strong">{item.policy_name}</td>
                <td>
                  {item.resource_name}
                  <div className="faint">{item.resource_type}</div>
                </td>
                <td style={{ maxWidth: 280 }}>
                  {reco[item.policy_name] ? (
                    <div className="reco">
                      <LightbulbIcon className="ico" size={15} />
                      <span>{reco[item.policy_name]}</span>
                    </div>
                  ) : (
                    <span className="faint">—</span>
                  )}
                </td>
                <td>{item.assignee ? item.assignee.split("@")[0] : <span className="faint">unassigned</span>}</td>
                <td className="muted">{age(item.opened_at)}</td>
                <td>
                  <span className={`badge ${item.status}`}>{item.status.replace("_", " ")}</span>
                </td>
                <td>
                  <div className="row">
                    {(ACTIONS[item.status] ?? []).map((action) => (
                      <button
                        key={action}
                        className="action secondary tiny"
                        onClick={() => promptAction(item, action)}
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
