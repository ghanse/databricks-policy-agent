import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import type { Policy, Settings } from "../types";
import { effectLabel, resourceTypeLabel, severityLabel, statusLabel } from "../labels";
import { FilterBar } from "./FilterBar";
import { PolicyDetail } from "./PolicyDetail";
import { PlusIcon } from "./icons";

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

export function PoliciesTab({ settings }: { settings: Settings | null }) {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState<FormState>(EMPTY);
  const [validation, setValidation] = useState("");
  const [importNote, setImportNote] = useState("");

  const [search, setSearch] = useState("");
  const [fType, setFType] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fSeverity, setFSeverity] = useState("");
  const [detail, setDetail] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

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
    setError("");
    try {
      const result = await api.validatePolicy(body());
      setValidation(result.valid ? "Valid ✓" : `Invalid: ${result.error}`);
    } catch (e) {
      setValidation(`Invalid JSON: ${e}`);
    }
  };

  const save = async () => {
    setError("");
    try {
      await api.savePolicy(body());
      setForm(EMPTY);
      setValidation("");
      setImportNote("");
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  const populateFrom = (policy: Policy) => {
    set({
      name: policy.policy,
      description: policy.description ?? "",
      resourceType: policy.resource_type,
      effect: policy.effect,
      severity: policy.severity,
      remediation: policy.remediation ?? "",
      rule: JSON.stringify(policy.rule, null, 2),
      match: policy.match ? JSON.stringify(policy.match, null, 2) : "",
    });
  };

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    setError("");
    setImportNote("");
    setValidation("");
    try {
      const { policies: parsed } = await api.parsePolicies(await file.text());
      if (!parsed.length) {
        setError("No policies found in that file.");
        return;
      }
      populateFrom(parsed[0]);
      setImportNote(
        parsed.length === 1
          ? "Loaded from file — review and save."
          : `Loaded the first of ${parsed.length} policies — review and save, then import the rest.`,
      );
    } catch (e) {
      setError(String(e));
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const resourceTypes = settings?.resource_types ?? ["cluster"];
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return policies.filter(
      (p) =>
        (!q || p.policy.toLowerCase().includes(q) || (p.description ?? "").toLowerCase().includes(q)) &&
        (!fType || p.resource_type === fType) &&
        (!fStatus || p.status === fStatus) &&
        (!fSeverity || p.severity === fSeverity),
    );
  }, [policies, search, fType, fStatus, fSeverity]);

  return (
    <>
      <div className="panel">
        <div className="spread" style={{ marginBottom: 14 }}>
          <div className="row">
            <button className="action secondary tiny" onClick={() => { setForm(EMPTY); setValidation(""); setImportNote(""); }}>
              <PlusIcon size={13} /> Add a policy
            </button>
            <button className="action secondary tiny" onClick={() => fileRef.current?.click()}>
              Import from YAML
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".yaml,.yml,text/yaml"
              style={{ display: "none" }}
              onChange={(e) => onFile(e.target.files?.[0])}
            />
          </div>
          {importNote && <span className="muted">{importNote}</span>}
        </div>
        {error && <div className="error">{error}</div>}
        <div className="row wrap" style={{ marginBottom: 12, alignItems: "flex-end" }}>
          <div style={{ flex: "2 1 200px" }}>
            <label className="field">Name</label>
            <input placeholder="policy-name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          </div>
          <div style={{ flex: "1 1 120px" }}>
            <label className="field">Resource type</label>
            <select value={form.resourceType} onChange={(e) => set({ resourceType: e.target.value })}>
              {resourceTypes.map((t) => (
                <option key={t} value={t}>
                  {resourceTypeLabel(t)}
                </option>
              ))}
            </select>
          </div>
          <div style={{ flex: "1 1 100px" }}>
            <label className="field">Effect</label>
            <select value={form.effect} onChange={(e) => set({ effect: e.target.value })}>
              <option value="deny">Deny</option>
              <option value="allow">Allow</option>
            </select>
          </div>
          <div style={{ flex: "1 1 100px" }}>
            <label className="field">Severity</label>
            <select value={form.severity} onChange={(e) => set({ severity: e.target.value })}>
              {["low", "medium", "high", "critical"].map((s) => (
                <option key={s} value={s}>
                  {severityLabel(s)}
                </option>
              ))}
            </select>
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
        <label className="field">Rule (condition tree, JSON)</label>
        <textarea value={form.rule} onChange={(e) => set({ rule: e.target.value })} />
        <label className="field" style={{ marginTop: 12 }}>
          Match selector (optional JSON)
        </label>
        <textarea
          style={{ minHeight: 90 }}
          placeholder="Leave empty to apply to all resources of this type"
          value={form.match}
          onChange={(e) => set({ match: e.target.value })}
        />
        <div className="row" style={{ marginTop: 12 }}>
          <button className="action secondary" onClick={validate}>
            Validate
          </button>
          <button className="action" onClick={save} disabled={!form.name}>
            Save draft
          </button>
          <span className="muted">{validation}</span>
        </div>
      </div>

      <div className="panel">
        <div className="spread" style={{ marginBottom: 12 }}>
          <h3 style={{ marginBottom: 0 }}>
            Policies
            <span className="hint">
              {filtered.length} of {policies.length}
            </span>
          </h3>
        </div>
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
                  <th>Name</th>
                  <th>Type</th>
                  <th>Effect</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Ver</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <tr key={p.policy} className="clickable" onClick={() => setDetail(p.policy)}>
                    <td>
                      <div className="cell-strong link">{p.policy}</div>
                      {p.description && <div className="faint">{p.description}</div>}
                    </td>
                    <td className="muted">{resourceTypeLabel(p.resource_type)}</td>
                    <td className="muted">{effectLabel(p.effect)}</td>
                    <td>
                      <span className={`badge ${p.severity}`}>{severityLabel(p.severity)}</span>
                    </td>
                    <td>
                      <span className={`badge ${p.status}`}>{statusLabel(p.status)}</span>
                    </td>
                    <td className="muted">{p.version}</td>
                    <td>
                      <button
                        className="action secondary tiny"
                        onClick={(e) => {
                          e.stopPropagation();
                          api.deletePolicy(p.policy).then(refresh);
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {detail && <PolicyDetail name={detail} onClose={() => setDetail(null)} />}
    </>
  );
}
