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
  const [enforcement, setEnforcement] = useState("advisory");
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
    enforcement,
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
        <h3>New / update policy</h3>
        {error && <div className="error">{error}</div>}
        <div className="row" style={{ marginBottom: 8 }}>
          <input placeholder="policy-name" value={name} onChange={(e) => setName(e.target.value)} />
          <select value={resourceType} onChange={(e) => setResourceType(e.target.value)}>
            {(settings?.resource_types ?? ["cluster"]).map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          <select value={effect} onChange={(e) => setEffect(e.target.value)}>
            <option value="deny">deny</option>
            <option value="allow">allow</option>
          </select>
          <select value={enforcement} onChange={(e) => setEnforcement(e.target.value)}>
            {["advisory", "soft", "hard"].map((level) => (
              <option key={level}>{level}</option>
            ))}
          </select>
        </div>
        <input
          placeholder="remediation guidance"
          value={remediation}
          onChange={(e) => setRemediation(e.target.value)}
          style={{ marginBottom: 8 }}
        />
        <textarea value={rule} onChange={(e) => setRule(e.target.value)} />
        <div className="row" style={{ marginTop: 8 }}>
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
        <h3>Policies</h3>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Effect</th>
              <th>Enforcement</th>
              <th>Status</th>
              <th>Version</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {policies.map((p) => (
              <tr key={p.policy}>
                <td>{p.policy}</td>
                <td>{p.resource_type}</td>
                <td>{p.effect}</td>
                <td>
                  <span className={`badge ${p.enforcement}`}>{p.enforcement}</span>
                </td>
                <td>
                  <span className={`badge ${p.status}`}>{p.status}</span>
                </td>
                <td>{p.version}</td>
                <td>
                  <button
                    className="action secondary"
                    onClick={() => api.deletePolicy(p.policy).then(refresh)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
