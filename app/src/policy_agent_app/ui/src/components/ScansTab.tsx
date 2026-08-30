import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Finding, ScanHeader, ScanResult, Settings } from "../types";
import { resourceTypeLabel, severityLabel } from "../labels";
import { useToast } from "../toast";
import { LightbulbIcon, ArrowLeftIcon } from "./icons";
import { SplitButton } from "./SplitButton";
import { FilterBar } from "./FilterBar";
import { Select } from "./Select";

const SEVERITY_ORDER = ["critical", "high", "medium", "low"];

function shortId(id: string): string {
  return id.slice(0, 8);
}

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function duration(start: string, finish: string): string {
  const ms = new Date(finish).getTime() - new Date(start).getTime();
  if (Number.isNaN(ms) || ms < 0) return "—";
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.round(s % 60)}s`;
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
  const [mode, setMode] = useState<"list" | "result">("list");
  const [result, setResult] = useState<ScanResult | null>(null);
  const [viewing, setViewing] = useState<{ header: ScanHeader | null; findings: Finding[] } | null>(null);
  const [history, setHistory] = useState<ScanHeader[]>([]);
  const [running, setRunning] = useState(false);
  const [search, setSearch] = useState("");
  const [fSeverity, setFSeverity] = useState("");
  const [fType, setFType] = useState("");
  const [fSource, setFSource] = useState("");
  const [fromDate, setFromDate] = useState("");
  const toast = useToast();

  const loadHistory = () => api.listScans().then(setHistory).catch(() => setHistory([]));
  useEffect(() => {
    loadHistory();
  }, []);

  const viewScan = async (header: ScanHeader | null, scanId: string) => {
    try {
      const findings = await api.scanFindings(scanId);
      setResult(null);
      setViewing({ header, findings });
      setMode("result");
    } catch (e) {
      toast.push(String(e), "error");
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
    setRunning(true);
    setViewing(null);
    try {
      const r = await api.runScan({ dry_run: dryRun });
      setResult(r);
      setMode("result");
      toast.push(dryRun ? "Dry run complete" : "Scan complete", "save");
      loadHistory();
    } catch (e) {
      toast.push(String(e), "error");
    } finally {
      setRunning(false);
    }
  };

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
  const sources = useMemo(() => [...new Set(history.map((h) => h.triggered_by))], [history]);

  const filteredViolations = useMemo(() => {
    const q = search.toLowerCase();
    return violations.filter(
      (f) =>
        (!q || f.policy_name.toLowerCase().includes(q) || (f.resource_name ?? "").toLowerCase().includes(q)) &&
        (!fSeverity || f.severity === fSeverity) &&
        (!fType || f.resource_type === fType),
    );
  }, [violations, search, fSeverity, fType]);

  const filteredHistory = useMemo(() => {
    const from = fromDate ? new Date(fromDate).getTime() : null;
    return history.filter(
      (h) =>
        (!fSource || h.triggered_by === fSource) &&
        (from == null || new Date(h.started_at).getTime() >= from),
    );
  }, [history, fSource, fromDate]);

  // ---- Result page ----
  if (mode === "result") {
    return (
      <>
        <button className="backlink" onClick={() => setMode("list")}>
          <ArrowLeftIcon size={15} /> Scans
        </button>
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
                    options: ["low", "medium", "high", "critical"].map((s) => ({ value: s, label: severityLabel(s) })),
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
      </>
    );
  }

  // ---- List page ----
  return (
    <>
      <div className="page-actions">
        <SplitButton
          label={running ? "Scanning…" : "Run scan"}
          disabled={running}
          onClick={() => run(false)}
          options={[{ label: "Dry run scan (validate only)", onSelect: () => run(true) }]}
        />
      </div>

      <div className="panel">
        <h3>
          Scan history
          <span className="hint">
            {filteredHistory.length} of {history.length}
          </span>
        </h3>
        <div className="filterbar">
          <label className="filter">
            <span>Source</span>
            <Select
              ariaLabel="Source"
              value={fSource}
              onChange={setFSource}
              options={[{ value: "", label: "All" }, ...sources.map((s) => ({ value: s, label: s }))]}
            />
          </label>
          <label className="filter">
            <span>Start on or after</span>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} style={{ width: "auto" }} />
          </label>
          {fromDate && (
            <button className="action secondary tiny" onClick={() => setFromDate("")}>
              Clear
            </button>
          )}
        </div>
        {history.length === 0 ? (
          <div className="empty">No scans yet. Run one above.</div>
        ) : filteredHistory.length === 0 ? (
          <div className="empty">No scans match the filter.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Start Time</th>
                  <th>Duration</th>
                  <th>Source</th>
                  <th>Evaluated</th>
                  <th>Violations</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.map((h) => (
                  <tr key={h.scan_id}>
                    <td>
                      <button className="linkbtn" onClick={() => viewScan(h, h.scan_id)}>
                        {fmtTime(h.started_at)}
                      </button>
                    </td>
                    <td className="muted">{duration(h.started_at, h.finished_at)}</td>
                    <td className="muted">{h.triggered_by}</td>
                    <td>{h.evaluated}</td>
                    <td>{Number(h.violations) > 0 ? <span className="badge high">{h.violations}</span> : "0"}</td>
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
