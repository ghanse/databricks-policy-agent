import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Policy, Settings } from "../types";
import { effectLabel, resourceTypeLabel, severityLabel, statusLabel } from "../labels";
import { useToast, type ToastKind } from "../toast";
import { transitionsFor } from "../policyActions";
import { FilterBar } from "./FilterBar";
import { ImportModal } from "./ImportModal";
import { PolicyPage } from "./PolicyPage";
import { Select } from "./Select";
import { SplitButton } from "./SplitButton";
import { NoteDialog, type NoteRequest } from "./NoteDialog";
import { TrashIcon } from "./icons";
import { SortTh, useSort, SEVERITY_RANK } from "../useSort";
import { usePage, PagerBar } from "../usePage";

const EXAMPLE_RULE = JSON.stringify(
  { any: [{ attribute: "owner_type", operator: "not_equals", value: "service_principal" }] },
  null,
  2,
);

interface FormState {
  name: string;
  description: string;
  resourceType: string;
  effect: string;
  severity: string;
  remediation: string;
  rule: string;
  match: string;
}

const EMPTY: FormState = {
  name: "",
  description: "",
  resourceType: "cluster",
  effect: "deny",
  severity: "medium",
  remediation: "",
  rule: EXAMPLE_RULE,
  match: "",
};

export function PoliciesTab({ settings, isAdmin }: { settings: Settings | null; isAdmin: boolean }) {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState<FormState>(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [validation, setValidation] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [dialog, setDialog] = useState<NoteRequest | null>(null);

  const [search, setSearch] = useState("");
  const [fType, setFType] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fSeverity, setFSeverity] = useState("");
  const [fEffect, setFEffect] = useState("");
  const [importing, setImporting] = useState(false);
  const toast = useToast();
  const sort = useSort<Policy>("name");

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }));
  const refresh = () => api.listPolicies().then(setPolicies).catch((e) => setError(String(e)));
  useEffect(() => {
    refresh();
  }, []);

  const body = () => {
    const data: Record<string, unknown> = {
      name: form.name,
      resource_type: form.resourceType,
      effect: form.effect,
      severity: form.severity,
      description: form.description,
      remediation: form.remediation,
      rule: JSON.parse(form.rule),
    };
    if (form.match.trim()) data.match = JSON.parse(form.match);
    return data;
  };

  const validate = async () => {
    try {
      const result = await api.validatePolicy(body());
      setValidation(result.valid ? "Valid ✓" : `Invalid: ${result.error}`);
    } catch (e) {
      setValidation(`Invalid JSON: ${e}`);
    }
  };

  const save = async () => {
    try {
      await api.savePolicy(body());
      setForm(EMPTY);
      setShowForm(false);
      setValidation("");
      toast.push("Policy saved as draft", "save");
      refresh();
    } catch (e) {
      toast.push(String(e), "error");
    }
  };

  const openNew = () => {
    setForm(EMPTY);
    setValidation("");
    setShowForm(true);
  };

  const doTransition = (policy: Policy, action: string, label: string, kind: ToastKind) => {
    setDialog({
      title: `${label} — ${policy.policy}`,
      description: "This is recorded as an immutable approval event.",
      confirmLabel: label,
      onConfirm: async (note) => {
        try {
          await api.transition(policy.policy, action, note);
          toast.push(`${label} ✓`, kind);
          refresh();
        } catch (e) {
          toast.push(String(e), "error");
        }
      },
    });
  };

  const doDelete = (policy: Policy) => {
    setDialog({
      title: `Delete ${policy.policy}?`,
      description: "This permanently removes the policy.",
      confirmLabel: "Delete",
      onConfirm: async () => {
        try {
          await api.deletePolicy(policy.policy);
          toast.push("Policy deleted", "delete");
          refresh();
        } catch (e) {
          toast.push(String(e), "error");
        }
      },
    });
  };

  const resourceTypes = settings?.resource_types ?? ["cluster"];
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return policies.filter(
      (p) =>
        (!q || p.policy.toLowerCase().includes(q) || (p.description ?? "").toLowerCase().includes(q)) &&
        (!fType || p.resource_type === fType) &&
        (!fStatus || p.status === fStatus) &&
        (!fSeverity || p.severity === fSeverity) &&
        (!fEffect || p.effect === fEffect),
    );
  }, [policies, search, fType, fStatus, fSeverity, fEffect]);

  const sorted = sort.apply(filtered, {
    name: (p) => p.policy.toLowerCase(),
    type: (p) => p.resource_type,
    effect: (p) => p.effect,
    severity: (p) => SEVERITY_RANK[p.severity] ?? -1,
    status: (p) => p.status,
    version: (p) => p.version,
  });
  const pager = usePage(sorted, 10);

  if (selected) {
    return (
      <PolicyPage
        name={selected}
        isAdmin={isAdmin}
        onBack={() => setSelected(null)}
        onChanged={refresh}
      />
    );
  }

  return (
    <>
      <div className="page-actions">
        <SplitButton
          label="Add a policy"
          onClick={openNew}
          options={[{ label: "Import from YAML", onSelect: () => setImporting(true) }]}
        />
      </div>
      {error && <div className="error">{error}</div>}

      {showForm && (
        <div className="panel">
          <h3>Add a policy</h3>
          <div className="row wrap" style={{ marginBottom: 12, alignItems: "flex-end" }}>
            <div style={{ flex: "2 1 200px" }}>
              <label className="field">Name</label>
              <input placeholder="policy-name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
            </div>
            <div style={{ flex: "1 1 120px" }}>
              <label className="field">Resource type</label>
              <Select
                block
                ariaLabel="Resource type"
                value={form.resourceType}
                onChange={(v) => set({ resourceType: v })}
                options={resourceTypes.map((t) => ({ value: t, label: resourceTypeLabel(t) }))}
              />
            </div>
            <div style={{ flex: "1 1 100px" }}>
              <label className="field">Effect</label>
              <Select
                block
                ariaLabel="Effect"
                value={form.effect}
                onChange={(v) => set({ effect: v })}
                options={[
                  { value: "deny", label: "Deny" },
                  { value: "allow", label: "Allow" },
                ]}
              />
            </div>
            <div style={{ flex: "1 1 100px" }}>
              <label className="field">Severity</label>
              <Select
                block
                ariaLabel="Severity"
                value={form.severity}
                onChange={(v) => set({ severity: v })}
                options={["low", "medium", "high", "critical"].map((s) => ({ value: s, label: severityLabel(s) }))}
              />
            </div>
          </div>
          <label className="field">Description</label>
          <input
            placeholder="What this policy checks"
            value={form.description}
            onChange={(e) => set({ description: e.target.value })}
            style={{ marginBottom: 12 }}
          />
          <label className="field">Recommended action (remediation guidance)</label>
          <input
            placeholder="What should an owner do to fix a violation?"
            value={form.remediation}
            onChange={(e) => set({ remediation: e.target.value })}
            style={{ marginBottom: 12 }}
          />
          <label className="field">Rule</label>
          <textarea value={form.rule} onChange={(e) => set({ rule: e.target.value })} />
          <label className="field" style={{ marginTop: 12 }}>
            Match selector
          </label>
          <textarea
            style={{ minHeight: 90 }}
            placeholder="Leave empty to apply to all resources of this type"
            value={form.match}
            onChange={(e) => set({ match: e.target.value })}
          />
          <div className="row" style={{ marginTop: 12 }}>
            <button className="action secondary" onClick={() => { setShowForm(false); setValidation(""); }}>
              Cancel
            </button>
            <button className="action secondary" onClick={validate}>
              Validate
            </button>
            <button className="action" onClick={save} disabled={!form.name}>
              Save draft
            </button>
            <span className="muted">{validation}</span>
          </div>
        </div>
      )}

      <div className="panel">
        <h3>
          Policies
          <span className="hint">
            {filtered.length} of {policies.length}
          </span>
        </h3>
        <FilterBar
          search={search}
          onSearch={setSearch}
          placeholder="Search by name or description…"
          filters={[
            {
              label: "Type",
              value: fType,
              onChange: setFType,
              options: resourceTypes.map((t) => ({ value: t, label: resourceTypeLabel(t) })),
            },
            {
              label: "Effect",
              value: fEffect,
              onChange: setFEffect,
              options: ["allow", "deny"].map((e) => ({ value: e, label: effectLabel(e) })),
            },
            {
              label: "Status",
              value: fStatus,
              onChange: setFStatus,
              options: ["draft", "in_review", "approved", "rejected", "archived"].map((s) => ({
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
          ]}
        />
        {filtered.length === 0 ? (
          <div className="empty">No matching policies.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <SortTh label="Name" field="name" sort={sort} />
                  <SortTh label="Type" field="type" sort={sort} />
                  <SortTh label="Effect" field="effect" sort={sort} />
                  <SortTh label="Severity" field="severity" sort={sort} />
                  <SortTh label="Status" field="status" sort={sort} />
                  <SortTh label="Version" field="version" sort={sort} />
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pager.pageRows.map((p) => (
                  <tr key={p.policy} className="clickable" onClick={() => setSelected(p.policy)}>
                    <td>
                      <div className="cell-strong link">{p.policy}</div>
                      {p.description && <div className="faint">{p.description}</div>}
                    </td>
                    <td>
                      <span className="badge neutral">{resourceTypeLabel(p.resource_type)}</span>
                    </td>
                    <td>
                      <span className="badge neutral">{effectLabel(p.effect)}</span>
                    </td>
                    <td>
                      <span className={`badge ${p.severity}`}>{severityLabel(p.severity)}</span>
                    </td>
                    <td>
                      <span className={`badge ${p.status}`}>{statusLabel(p.status)}</span>
                    </td>
                    <td>
                      <span className="badge neutral">Version {p.version}</span>
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <div className="row">
                        {transitionsFor(p.status).map((t) => {
                          const Icon = t.icon;
                          return (
                            <button
                              key={t.action}
                              className={`icon-btn act-${t.color}`}
                              title={t.label}
                              onClick={() => doTransition(p, t.action, t.label, t.kind)}
                            >
                              <Icon size={15} />
                            </button>
                          );
                        })}
                        {isAdmin && (
                          <button className="icon-btn act-danger" title="Delete" onClick={() => doDelete(p)}>
                            <TrashIcon size={15} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <PagerBar pager={pager} />
          </div>
        )}
      </div>
      <NoteDialog request={dialog} onClose={() => setDialog(null)} />
      {importing && <ImportModal onClose={() => setImporting(false)} onImported={refresh} />}
    </>
  );
}
