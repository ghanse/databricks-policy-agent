import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Policy, Remediation } from "../types";
import { resourceTypeLabel, severityLabel, statusLabel } from "../labels";
import { useToast, type ToastKind } from "../toast";
import { AssignIcon, CheckIcon, ExternalIcon, LightbulbIcon, XIcon } from "./icons";
import { NoteDialog, type NoteRequest } from "./NoteDialog";
import { FilterBar } from "./FilterBar";
import { SortTh, useSort, SEVERITY_RANK } from "../useSort";
import { usePage, PagerBar } from "../usePage";
import { resourceUrl } from "../resourceUrl";
import type { ActionColor } from "../policyActions";

type IconType = (props: { className?: string; size?: number }) => JSX.Element;

const ACTIONS: Record<string, { action: string; label: string; icon: IconType; kind: ToastKind; color: ActionColor }[]> = {
  open: [
    { action: "advance", label: "Assign", icon: AssignIcon, kind: "save", color: "neutral" },
    { action: "resolve", label: "Resolve", icon: CheckIcon, kind: "save", color: "ok" },
    { action: "waive", label: "Waive", icon: XIcon, kind: "delete", color: "danger" },
  ],
  in_progress: [
    { action: "resolve", label: "Resolve", icon: CheckIcon, kind: "save", color: "ok" },
    { action: "waive", label: "Waive", icon: XIcon, kind: "delete", color: "danger" },
  ],
};

const UNASSIGNED = "__unassigned__";

const ACTION_HELP: Record<string, string> = {
  advance: "Assign an owner and mark this violation as in progress.",
  resolve: "Record that the underlying violation has been fixed.",
  waive: "Knowingly accept this violation; it stays on the audit trail.",
};


export function RemediationsTab({
  onOpenScan,
  workspaceUrl,
}: {
  onOpenScan: (scanId: string) => void;
  workspaceUrl: string;
}) {
  const [items, setItems] = useState<Remediation[]>([]);
  const [reco, setReco] = useState<Record<string, string>>({});
  const [dialog, setDialog] = useState<NoteRequest | null>(null);
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fSeverity, setFSeverity] = useState("");
  const [fType, setFType] = useState("");
  const [fOwner, setFOwner] = useState("");
  const sort = useSort<Remediation>("severity");

  const refresh = () => api.listRemediations().then(setItems).catch((e) => toast.push(String(e), "error"));
  useEffect(() => {
    refresh();
    api
      .listPolicies()
      .then((policies: Policy[]) =>
        setReco(Object.fromEntries(policies.map((p) => [p.policy, p.remediation ?? ""]))),
      )
      .catch(() => setReco({}));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const promptAction = (item: Remediation, action: string, label: string, kind: ToastKind) => {
    setDialog({
      title: `${label} — ${item.policy_name}`,
      description: ACTION_HELP[action],
      confirmLabel: label,
      withAssignee: action === "advance",
      onConfirm: async (note, assignee) => {
        try {
          await api.remediationAction(item.remediation_id, action, note, assignee);
          toast.push(`${label} ✓`, kind);
          refresh();
        } catch (e) {
          toast.push(String(e), "error");
        }
      },
    });
  };

  const open = items.filter((i) => i.status === "open" || i.status === "in_progress");
  const owners = useMemo(
    () => [...new Set(items.map((i) => i.assignee).filter(Boolean))] as string[],
    [items],
  );
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return items.filter(
      (i) =>
        (!q ||
          i.policy_name.toLowerCase().includes(q) ||
          (i.resource_name ?? "").toLowerCase().includes(q)) &&
        (!fStatus || i.status === fStatus) &&
        (!fSeverity || i.severity === fSeverity) &&
        (!fType || i.resource_type === fType) &&
        (!fOwner || (fOwner === UNASSIGNED ? !i.assignee : i.assignee === fOwner)),
    );
  }, [items, search, fStatus, fSeverity, fType, fOwner]);

  const sorted = sort.apply(filtered, {
    severity: (i) => SEVERITY_RANK[i.severity] ?? -1,
    policy: (i) => i.policy_name.toLowerCase(),
    type: (i) => i.resource_type,
    resource: (i) => (i.resource_name ?? "").toLowerCase(),
    owner: (i) => (i.assignee ?? "").toLowerCase(),
    status: (i) => i.status,
  });
  const pager = usePage(sorted, 10);

  return (
    <div className="panel">
      <h3>
        Remediations
        <span className="hint">
          {open.length} open · {items.length} total
        </span>
      </h3>
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
          {
            label: "Owner",
            value: fOwner,
            onChange: setFOwner,
            options: [
              { value: UNASSIGNED, label: "Unassigned" },
              ...owners.map((o) => ({ value: o, label: o })),
            ],
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
              <SortTh label="Severity" field="severity" sort={sort} />
              <SortTh label="Policy" field="policy" sort={sort} />
              <SortTh label="Type" field="type" sort={sort} />
              <SortTh label="Resource" field="resource" sort={sort} />
              <th>Recommended action</th>
              <SortTh label="Owner" field="owner" sort={sort} />
              <th>Opened by</th>
              <SortTh label="Status" field="status" sort={sort} />
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pager.pageRows.map((item) => (
              <tr key={item.remediation_id}>
                <td>
                  <span className={`badge ${item.severity}`}>{severityLabel(item.severity)}</span>
                </td>
                <td className="cell-strong">{item.policy_name}</td>
                <td>
                  <span className="badge neutral">{resourceTypeLabel(item.resource_type)}</span>
                </td>
                <td>
                  {(() => {
                    const url = resourceUrl(workspaceUrl, item.resource_type, item.resource_id);
                    return url ? (
                      <a className="reslink" href={url} target="_blank" rel="noreferrer">
                        {item.resource_name} <ExternalIcon size={12} />
                      </a>
                    ) : (
                      item.resource_name
                    );
                  })()}
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
                <td>{item.assignee ? item.assignee : <span className="faint">Unassigned</span>}</td>
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
                    {(ACTIONS[item.status] ?? []).map((a) => {
                      const Icon = a.icon;
                      return (
                        <button
                          key={a.action}
                          className={`icon-btn act-${a.color}`}
                          title={a.label}
                          onClick={() => promptAction(item, a.action, a.label, a.kind)}
                        >
                          <Icon size={15} />
                        </button>
                      );
                    })}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <PagerBar pager={pager} />
        </div>
      )}
      <NoteDialog request={dialog} onClose={() => setDialog(null)} />
    </div>
  );
}
