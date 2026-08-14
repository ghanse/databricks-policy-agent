import { useEffect, useState } from "react";
import { api } from "../api";
import type { Remediation } from "../types";

const ACTIONS: Record<string, string[]> = {
  open: ["advance", "resolve", "waive"],
  in_progress: ["resolve", "waive"],
};

export function RemediationsTab() {
  const [items, setItems] = useState<Remediation[]>([]);
  const [error, setError] = useState("");

  const refresh = () => api.listRemediations().then(setItems).catch((e) => setError(String(e)));
  useEffect(() => {
    refresh();
  }, []);

  const act = async (id: string, action: string) => {
    setError("");
    const note = window.prompt(`Note for ${action}?`) ?? "";
    try {
      await api.remediationAction(id, action, note);
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="panel">
      <h3>Remediation cycle</h3>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>Severity</th>
            <th>Policy</th>
            <th>Resource</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.remediation_id}>
              <td>
                <span className={`badge ${item.severity}`}>{item.severity}</span>
              </td>
              <td>{item.policy_name}</td>
              <td>
                {item.resource_name}
                <div className="muted">{item.resource_type}</div>
              </td>
              <td>
                <span className={`badge ${item.status}`}>{item.status}</span>
              </td>
              <td>
                <div className="row">
                  {(ACTIONS[item.status] ?? []).map((action) => (
                    <button
                      key={action}
                      className="action secondary"
                      onClick={() => act(item.remediation_id, action)}
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
  );
}
