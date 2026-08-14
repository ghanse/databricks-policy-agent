import { useEffect, useState } from "react";
import { api } from "../api";
import type { Policy } from "../types";

const ACTIONS: Record<string, string[]> = {
  draft: ["submit"],
  rejected: ["submit"],
  in_review: ["approve", "reject"],
  approved: ["archive"],
};

export function ApprovalsTab() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [error, setError] = useState("");

  const refresh = () => api.listPolicies().then(setPolicies).catch((e) => setError(String(e)));
  useEffect(() => {
    refresh();
  }, []);

  const act = async (name: string, action: string) => {
    setError("");
    const note = window.prompt(`Note for ${action}?`) ?? "";
    try {
      await api.transition(name, action, note);
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="panel">
      <h3>Approval workflow</h3>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>Policy</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {policies.map((p) => (
            <tr key={p.policy}>
              <td>{p.policy}</td>
              <td>
                <span className={`badge ${p.status}`}>{p.status}</span>
              </td>
              <td>
                <div className="row">
                  {(ACTIONS[p.status] ?? []).map((action) => (
                    <button
                      key={action}
                      className="action secondary"
                      onClick={() => act(p.policy, action)}
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
