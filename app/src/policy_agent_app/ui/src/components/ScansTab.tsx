import { useState } from "react";
import { api } from "../api";
import type { ScanResult, Settings } from "../types";
import { LightbulbIcon } from "./icons";

const SEVERITY_ORDER = ["critical", "high", "medium", "low"];

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

  const bySeverity = result?.summary.violations_by_severity ?? {};
  const rate = result ? Math.round(result.summary.compliance_rate * 100) : 0;

  return (
    <>
      <div className="panel">
        <h3>Run a scan</h3>
        {error && <div className="error">{error}</div>}
        <div className="spread">
          <div>
            <p className="muted" style={{ margin: 0 }}>
              Evaluates every approved policy across{" "}
              {(settings?.resource_types ?? []).join(", ") || "all resource types"}.
            </p>
            <label className="row" style={{ marginTop: 10 }}>
              <input
                type="checkbox"
                checked={dryRun}
                style={{ width: "auto" }}
                onChange={(e) => setDryRun(e.target.checked)}
              />
              <span className="muted">Dry run — evaluate without persisting results</span>
            </label>
          </div>
          <button className="action" onClick={run} disabled={running}>
            {running ? "Scanning…" : "Run scan"}
          </button>
        </div>
      </div>

      {result && (
        <>
          <div className="panel grid">
            <div className="stat">
              <div className="value">{result.summary.evaluated}</div>
              <div className="label">Evaluated</div>
            </div>
            <div className="stat danger">
              <div className="value">{result.summary.violations}</div>
              <div className="label">Violations</div>
            </div>
            <div className="stat ok">
              <div className="value">{result.summary.compliant}</div>
              <div className="label">Compliant</div>
            </div>
            <div className="stat accent">
              <div className="value">{rate}%</div>
              <div className="label">Compliance</div>
              <div className="meter">
                <span style={{ width: `${rate}%` }} />
              </div>
            </div>
          </div>

          <div className="panel">
            <h3>
              Violations
              <span className="hint">
                {SEVERITY_ORDER.filter((s) => bySeverity[s]).map((s) => (
                  <span key={s} className={`badge ${s}`} style={{ marginLeft: 6 }}>
                    {bySeverity[s]} {s}
                  </span>
                ))}
              </span>
            </h3>
            {result.violations.length === 0 ? (
              <div className="empty">No violations — everything scanned is compliant. 🎉</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Policy</th>
                    <th>Resource</th>
                    <th>Recommended fix</th>
                  </tr>
                </thead>
                <tbody>
                  {result.violations.map((f, i) => (
                    <tr key={i}>
                      <td>
                        <span className={`badge ${f.severity}`}>{f.severity}</span>
                      </td>
                      <td className="cell-strong">
                        {f.policy_name}
                        <div className="faint">{f.message}</div>
                      </td>
                      <td>
                        {f.resource_name}
                        <div className="faint">{f.resource_type}</div>
                      </td>
                      <td style={{ maxWidth: 300 }}>
                        {f.remediation ? (
                          <div className="reco">
                            <LightbulbIcon className="ico" size={15} />
                            <span>{f.remediation}</span>
                          </div>
                        ) : (
                          <span className="faint">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </>
  );
}
