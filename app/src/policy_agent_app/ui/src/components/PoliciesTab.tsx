import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Policy, Settings } from "../types";
import { effectLabel, resourceTypeLabel, severityLabel, statusLabel } from "../labels";
import { FilterBar } from "./FilterBar";
import { PolicyDetail } from "./PolicyDetail";
import { ImportDialog } from "./ImportDialog";

const EXAMPLE_RULE = JSON.stringify(
  { any: [{ attribute: "owner_type", operator: "not_equals", value: "service_principal" }] },
  null,
  2,
);

export function PoliciesTab({ settings }: { settings: Settings | null }) {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [resourceType, setResourceType] = useState("cluster");
  const [effect, setEffect] = useState("deny");
  const [severity, setSeverity] = useState("medium");
  const [remediation, setRemediation] = useState("");
  const [rule, setRule] = useState(EXAMPLE_RULE);
  const [validation, setValidation] = useState("");

  const [search, setSearch] = useState("");
  const [fType, setFType] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fSeverity, setFSeverity] = useState("");
  const [detail, setDetail] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  const refresh = () => api.listPolicies().then(setPolicies).catch((e) => setError(String(e)));
  useEffect(() => {
    refresh();
  }, []);

  const body = () => ({
    name,
    resource_type: resourceType,
    effect,
    severity,
    remediation,
    rule: JSON.parse(rule),
  });

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
      setName("");
      setValidation("");
      refresh();
    } catch (e) {
      setError(String(e));
    }
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
        <h3>
          New / update policy
          <span className="hint">saved as a draft for review</span>
        </h3>
        {error && <div className="error">{error}</div>}
        <div className="row wrap" style={{ marginBottom: 12, alignItems: "flex-end" }}>
          <div style={{ flex: "2 1 200px" }}>
            <label className="field">Name</label>
            <input placeholder="policy-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div style={{ flex: "1 1 120px" }}>
            <label className="field">Resource type</label>
            <select value={resourceType} onChange={(e) => setResourceType(e.target.value)}>
              {resourceTypes.map((t) => (
                <option key={t} value={t}>
                  {resourceTypeLabel(t)}
                </option>
              ))}
            </select>
          </div>
          <div style={{ flex: "1 1 100px" }}>
            <label className="field">Effect</label>
            <select value={effect} onChange={(e) => setEffect(e.target.value)}>
              <option value="deny">Deny</option>
              <option value="allow">Allow</option>
            </select>
          </div>
          <div style={{ flex: "1 1 100px" }}>
            <label className="field">Severity</label>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {["low", "medium", "high", "critical"].map((s) => (
                <option key={s} value={s}>
                  {severityLabel(s)}
                </option>
              ))}
            </select>
          </div>
        </div>
        <label className="field">Recommended action (remediation guidance)</label>
        <input
          placeholder="What should an owner do to fix a violation?"
          value={remediation}
          onChange={(e) => setRemediation(e.target.value)}
          style={{ marginBottom: 12 }}
        />
        <label className="field">Rule (condition tree, JSON)</label>
        <textarea value={rule} onChange={(e) => setRule(e.target.value)} />
        <div className="row" style={{ marginTop: 12 }}>
          <button className="action secondary" onClick={validate}>
            Validate
          </button>
          <button className="action" onClick={save} disabled={!name}>
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
          <button className="action secondary tiny" onClick={() => setImporting(true)}>
            Import YAML
          </button>
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
        )}
      </div>

      {detail && <PolicyDetail name={detail} onClose={() => setDetail(null)} />}
      {importing && <ImportDialog onClose={() => setImporting(false)} onImported={refresh} />}
    </>
  );
}
