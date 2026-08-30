import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Finding, ScanHeader, ScanResult, Settings } from "../types";
import { resourceTypeLabel, severityLabel } from "../labels";
import { LightbulbIcon } from "./icons";
import { SplitButton } from "./SplitButton";
import { FilterBar } from "./FilterBar";

const SEVERITY_ORDER = ["critical", "high", "medium", "low"];

function shortId(id: string): string {
  return id.slice(0, 8);
}

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export function ScansTab({
  settings,
  focusScanId,
  onFocusHandled,
}: {
  settings: Settings | null;
  focusScanId: string | null;
  onFocusHandled: () => void;
}) {
  const [result, setResult] = useState<ScanResult | null>(null);
  const [viewing, setViewing] = useState<{ header: ScanHeader | null; findings: Finding[] } | null>(null);
  const [history, setHistory] = useState<ScanHeader[]>([]);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [search, setSearch] = useState("");
  const [fSeverity, setFSeverity] = useState("");
  const [fType, setFType] = useState("");

  const loadHistory = () => api.listScans().then(setHistory).catch(() => setHistory([]));
  useEffect(() => {
    loadHistory();
  }, []);

  const viewScan = async (header: ScanHeader | null, scanId: string) => {
    setError("");
    setResult(null);
    try {
      const findings = await api.scanFindings(scanId);
      setViewing({ header, findings });
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    if (focusScanId) {
      viewScan(history.find((h) => h.scan_id === focusScanId) ?? null, focusScanId);
      onFocusHandled();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusScanId]);

  const run = async (dryRun: boolean) => {
    setError("");
    setRunning(true);
    setViewing(null);
    try {
      setResult(await api.runScan({ dry_run: dryRun }));
      loadHistory();
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  // Normalise whichever scan is on screen (fresh run or a selected history row).
  const violations: Finding[] = result
    ? result.violations
    : (viewing?.findings ?? []).filter((f) => !f.compliant);
  const stats = result
    ? {
        evaluated: result.summary.evaluated,
        compliant: result.summary.compliant,
        violations: result.summary.violations,
        rate: Math.round(result.summary.compliance_rate * 100),
        bySeverity: result.summary.violations_by_severity,
      }
    : viewing?.header
      ? {
          evaluated: Number(viewing.header.evaluated),
          compliant: Number(viewing.header.compliant),
          violations: Number(viewing.header.violations),
          rate:
            Number(viewing.header.evaluated) > 0
              ? Math.round((Number(viewing.header.compliant) / Number(viewing.header.evaluated)) * 100)
              : 0,
          bySeverity: {} as Record<string, number>,
        }
      : null;

  const shownScanId = result?.scan_id ?? viewing?.header?.scan_id ?? null;
  const resourceTypes = settings?.resource_types ?? [];

  const filteredViolations = useMemo(() => {
    const q = search.toLowerCase();
    return violations.filter(
      (f) =>
        (!q ||
          f.policy_name.toLowerCase().includes(q) ||
          (f.resource_name ?? "").toLowerCase().includes(q)) &&
        (!fSeverity || f.severity === fSeverity) &&
        (!fType || f.resource_type === fType),
    );
  }, [violations, search, fSeverity, fType]);

  return (
    <>
      <div className="page-actions">
        <SplitButton
          label={running ? "Scanning…" : "Run scan"}
          disabled={running}
          onClick={() => run(false)}
          options={[{ label: "Dry run scan (don't persist)", onSelect: () => run(true) }]}
        />
      </div>
      {error && <div className="error">{error}</div>}

      {stats && (
        <>
          <div className="panel grid">
            <div className="stat">
              <div className="value">{stats.evaluated}</div>
              <div className="label">Evaluated</div>
            </div>
            <div className="stat danger">
              <div className="value">{stats.violations}</div>
              <div className="label">Violations</div>
            </div>
            <div className="stat ok">
              <div className="value">{stats.compliant}</div>
              <div className="label">Compliant</div>
            </div>
            <div className="stat accent">
              <div className="value">{stats.rate}%</div>
              <div className="label">Compliance</div>
              <div className="meter">
                <span style={{ width: `${stats.rate}%` }} />
              </div>
            </div>
          </div>

          <div className="panel">
            <h3>
              Violations
              {shownScanId && <span className="hint">scan {shortId(shownScanId)}</span>}
              <span className="hint">
                {SEVERITY_ORDER.filter((s) => stats.bySeverity[s]).map((s) => (
                  <span key={s} className={`badge ${s}`} style={{ marginLeft: 6 }}>
                    {stats.bySeverity[s]} {severityLabel(s)}
                  </span>
                ))}
              </span>
            </h3>
            <FilterBar
              search={search}
              onSearch={setSearch}
              placeholder="Search by policy or resource…"
              filters={[
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
                  options: resourceTypes.map((t) => ({ value: t, label: resourceTypeLabel(t) })),
                },
              ]}
            />
            {filteredViolations.length === 0 ? (
              <div className="empty">No violations — everything scanned is compliant. 🎉</div>
            ) : (
              <div className="table-wrap">
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
                  {filteredViolations.map((f, i) => (
                    <tr key={i}>
                      <td>
                        <span className={`badge ${f.severity}`}>{severityLabel(f.severity)}</span>
                      </td>
                      <td className="cell-strong">
                        {f.policy_name}
                        <div className="faint">{f.message}</div>
                      </td>
                      <td>
                        {f.resource_name}
                        <div className="faint">{resourceTypeLabel(f.resource_type)}</div>
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
              </div>
            )}
          </div>
        </>
      )}

      <div className="panel">
        <h3>
          Scan history
          <span className="hint">{history.length} scans</span>
        </h3>
        {history.length === 0 ? (
          <div className="empty">No scans yet. Run one above.</div>
        ) : (
          <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Scan</th>
                <th>Triggered by</th>
                <th>Evaluated</th>
                <th>Violations</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr
                  key={h.scan_id}
                  className={`clickable ${h.scan_id === shownScanId ? "selected-row" : ""}`}
                  onClick={() => viewScan(h, h.scan_id)}
                >
                  <td>{when(h.started_at)}</td>
                  <td className="mono">{shortId(h.scan_id)}</td>
                  <td className="muted">{h.triggered_by}</td>
                  <td>{h.evaluated}</td>
                  <td>{Number(h.violations) > 0 ? <span className="badge high">{h.violations}</span> : "0"}</td>
                  <td className="link">View</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </>
  );
}
