import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Policy, Remediation } from "../types";
import { resourceTypeLabel, severityLabel, statusLabel } from "../labels";
import { LightbulbIcon } from "./icons";
import { NoteDialog, type NoteRequest } from "./NoteDialog";
import { FilterBar } from "./FilterBar";

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

export function RemediationsTab({ onOpenScan }: { onOpenScan: (scanId: string) => void }) {
  const [items, setItems] = useState<Remediation[]>([]);
  const [reco, setReco] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState<NoteRequest | null>(null);
  const [search, setSearch] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fSeverity, setFSeverity] = useState("");
  const [fType, setFType] = useState("");

  const refresh = () => api.listRemediations().then(setItems).catch((e) => setError(String(e)));
  useEffect(() => {
    refresh();
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
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return items.filter(
      (i) =>
        (!q ||
          i.policy_name.toLowerCase().includes(q) ||
          (i.resource_name ?? "").toLowerCase().includes(q)) &&
        (!fStatus || i.status === fStatus) &&
        (!fSeverity || i.severity === fSeverity) &&
        (!fType || i.resource_type === fType),
    );
  }, [items, search, fStatus, fSeverity, fType]);

  return (
    <div className="panel">
      <h3>
        Remediation cycle
        <span className="hint">
          {open.length} open · {items.length} total
        </span>
      </h3>
      {error && <div className="error">{error}</div>}
      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Search by policy or resource…"
        filters={[
          {
            label: "Status",
            value: fStatus,
            onChange: setFStatus,
            options: ["open", "in_progress", "resolved", "waived"].map((s) => ({
              value: s,
              label: statusLabel(s),
            })),
          },
          {
            label: "Severity",
            value: fSeverity,
            onChange: setFSeverity,
            options: ["low", "medium", "high", "critical"].map((s) => ({
              value: s,
              label: severityLabel(s),
            })),
          },
          {
            label: "Type",
            value: fType,
            onChange: setFType,
            options: [...new Set(items.map((i) => i.resource_type))].map((t) => ({
              value: t,
              label: resourceTypeLabel(t),
            })),
          },
        ]}
      />
      {items.length === 0 ? (
        <div className="empty">No remediation items yet. Run a scan to open items for any violations.</div>
      ) : filtered.length === 0 ? (
        <div className="empty">No matching remediation items.</div>
      ) : (
        <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Policy</th>
              <th>Resource</th>
              <th>Recommended action</th>
              <th>Owner</th>
              <th>Age</th>
              <th>Opened by</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.remediation_id}>
                <td>
                  <span className={`badge ${item.severity}`}>{severityLabel(item.severity)}</span>
                </td>
                <td className="cell-strong">{item.policy_name}</td>
                <td>
                  {item.resource_name}
                  <div className="faint">{resourceTypeLabel(item.resource_type)}</div>
                </td>
                <td style={{ maxWidth: 260 }}>
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
                  {item.scan_id ? (
                    <button className="linkbtn mono" onClick={() => onOpenScan(item.scan_id)}>
                      {item.scan_id.slice(0, 8)}
                    </button>
                  ) : (
                    <span className="faint">—</span>
                  )}
                </td>
                <td>
                  <span className={`badge ${item.status}`}>{statusLabel(item.status)}</span>
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
        </div>
      )}
      <NoteDialog request={dialog} onClose={() => setDialog(null)} />
    </div>
  );
}
