import { useState } from "react";
import { api } from "../api";
import type { ScanResult, Settings } from "../types";

export function ScansTab({ settings }: { settings: Settings | null }) {
  const [result, setResult] = useState<ScanResult | null>(null);
  const [dryRun, setDryRun] = useState(false);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  const run = async () => {
    setError("");
    setRunning(true);
    try {
      setResult(await api.runScan({ dry_run: dryRun }));
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <div className="panel">
        <h3>Run a scan</h3>
        {error && <div className="error">{error}</div>}
        <div className="row">
          <label className="row">
            <input
              type="checkbox"
              checked={dryRun}
              style={{ width: "auto" }}
              onChange={(e) => setDryRun(e.target.checked)}
            />
            <span className="muted">Dry run (do not persist)</span>
          </label>
          <button className="action" onClick={run} disabled={running}>
            {running ? "Scanning…" : "Scan approved policies"}
          </button>
        </div>
        <p className="muted">
          Scans every approved policy across{" "}
          {(settings?.resource_types ?? []).join(", ") || "all resource types"}.
        </p>
      </div>

      {result && (
        <>
          <div className="panel grid">
            <div className="stat">
              <div className="value">{result.summary.evaluated}</div>
              <div className="label">Evaluated</div>
            </div>
            <div className="stat">
              <div className="value">{result.summary.violations}</div>
              <div className="label">Violations</div>
            </div>
            <div className="stat">
              <div className="value">{result.summary.compliant}</div>
              <div className="label">Compliant</div>
            </div>
            <div className="stat">
              <div className="value">{Math.round(result.summary.compliance_rate * 100)}%</div>
              <div className="label">Compliance</div>
            </div>
          </div>
          <div className="panel">
            <h3>Violations</h3>
            <table>
              <thead>
                <tr>
                  <th>Enforcement</th>
                  <th>Policy</th>
                  <th>Resource</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {result.violations.map((f, i) => (
                  <tr key={i}>
                    <td>
                      <span className={`badge ${f.enforcement_level}`}>{f.enforcement_level}</span>
                    </td>
                    <td>{f.policy_name}</td>
                    <td>
                      {f.resource_name}
                      <div className="muted">{f.resource_type}</div>
                    </td>
                    <td>{f.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
