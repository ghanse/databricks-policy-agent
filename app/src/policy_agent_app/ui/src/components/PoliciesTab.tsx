import { useEffect, useState } from "react";
import { api } from "../api";
import type { Policy, Settings } from "../types";

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
              {(settings?.resource_types ?? ["cluster"]).map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </div>
          <div style={{ flex: "1 1 100px" }}>
            <label className="field">Effect</label>
            <select value={effect} onChange={(e) => setEffect(e.target.value)}>
              <option value="deny">deny</option>
              <option value="allow">allow</option>
            </select>
          </div>
          <div style={{ flex: "1 1 100px" }}>
            <label className="field">Severity</label>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {["low", "medium", "high", "critical"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>
        <label className="field">Remediation guidance</label>
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
        <h3>
          Policies
          <span className="hint">{policies.length} defined</span>
        </h3>
        {policies.length === 0 ? (
          <div className="empty">No policies yet. Create one above to get started.</div>
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
              {policies.map((p) => (
                <tr key={p.policy}>
                  <td>
                    <div className="cell-strong">{p.policy}</div>
                    {p.description && <div className="faint">{p.description}</div>}
                  </td>
                  <td className="muted">{p.resource_type}</td>
                  <td className="muted">{p.effect}</td>
                  <td>
                    <span className={`badge ${p.severity}`}>{p.severity}</span>
                  </td>
                  <td>
                    <span className={`badge ${p.status}`}>{p.status.replace("_", " ")}</span>
                  </td>
                  <td className="muted">{p.version}</td>
                  <td>
                    <button
                      className="action secondary tiny"
                      onClick={() => api.deletePolicy(p.policy).then(refresh)}
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
    </>
  );
}
