import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Finding, ScanHeader, ScanResult, Settings } from "../types";
import { resourceTypeLabel, severityLabel } from "../labels";
import { useToast } from "../toast";
import { useSort, SortTh, SEVERITY_RANK } from "../useSort";
import { CheckIcon, ChevronIcon, LightbulbIcon } from "./icons";
import { SplitButton } from "./SplitButton";
import { FilterBar } from "./FilterBar";
import { Select } from "./Select";

function shortId(id: string): string {
  return id.slice(0, 8);
}
function fmtTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}
function durationMs(start: string, finish: string): number {
  return new Date(finish).getTime() - new Date(start).getTime();
}
function fmtDuration(ms: number): string {
  if (Number.isNaN(ms) || ms < 0) return "—";
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
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
  const [paneOpen, setPaneOpen] = useState(true);
  const [search, setSearch] = useState("");
  const [fSeverity, setFSeverity] = useState("");
  const [fType, setFType] = useState("");
  const [fSource, setFSource] = useState("");
  const [fromDate, setFromDate] = useState("");
  const toast = useToast();
  const histSort = useSort<ScanHeader>("started_at");
  const violSort = useSort<Finding>("severity");

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

  // Unified detail model for the results pane.
  const details = result
    ? {
        scanId: result.scan_id,
        start: result.started_at,
        end: result.finished_at,
        source: "app",
        evaluated: result.summary.evaluated,
        compliant: result.summary.compliant,
        violations: result.summary.violations,
      }
    : viewing?.header
      ? {
          scanId: viewing.header.scan_id,
          start: viewing.header.started_at,
          end: viewing.header.finished_at,
          source: viewing.header.triggered_by,
          evaluated: Number(viewing.header.evaluated),
          compliant: Number(viewing.header.compliant),
          violations: Number(viewing.header.violations),
        }
      : viewing
        ? { scanId: "", start: "", end: "", source: "—", evaluated: 0, compliant: 0, violations: 0 }
        : null;

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
  const sortedViolations = violSort.apply(filteredViolations, {
    severity: (f) => SEVERITY_RANK[f.severity] ?? -1,
    policy: (f) => f.policy_name.toLowerCase(),
    resource: (f) => (f.resource_name ?? "").toLowerCase(),
  });

  const filteredHistory = useMemo(() => {
    const from = fromDate ? new Date(fromDate).getTime() : null;
    return history.filter(
      (h) =>
        (!fSource || h.triggered_by === fSource) &&
        (from == null || new Date(h.started_at).getTime() >= from),
    );
  }, [history, fSource, fromDate]);
  const sortedHistory = histSort.apply(filteredHistory, {
    started_at: (h) => new Date(h.started_at).getTime(),
    duration: (h) => durationMs(h.started_at, h.finished_at),
    source: (h) => h.triggered_by,
    evaluated: (h) => Number(h.evaluated),
    violations: (h) => Number(h.violations),
  });

  // ---- Result page ----
  if (mode === "result" && details) {
    const pct = (n: number) => (details.evaluated > 0 ? Math.round((n / details.evaluated) * 100) : 0);
    return (
      <>
        <div className="crumbs">
          <button onClick={() => setMode("list")}>Scans</button>
          <span className="sep">/</span>
          <span className="here mono">{shortId(details.scanId) || "result"}</span>
        </div>

        <div className={`scan-layout ${paneOpen ? "" : "collapsed"}`}>
          <div className="panel" style={{ marginBottom: 0 }}>
            <h3>
              Violations
              <span className="hint">{sortedViolations.length} shown</span>
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
            {sortedViolations.length === 0 ? (
              <div className="empty">No violations — everything scanned is compliant. 🎉</div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <SortTh label="Severity" field="severity" sort={violSort} />
                      <SortTh label="Policy" field="policy" sort={violSort} />
                      <SortTh label="Resource" field="resource" sort={violSort} />
                      <th>Recommended fix</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedViolations.map((f, i) => (
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

          {paneOpen ? (
            <div className="panel detail-pane" style={{ marginBottom: 0 }}>
              <div className="pane-head">
                <h3>Scan details</h3>
                <button className="chev" title="Collapse" onClick={() => setPaneOpen(false)}>
                  <ChevronIcon size={16} />
                </button>
              </div>
              <dl className="detail-list">
                <dt>Scan ID</dt>
                <dd className="mono">{details.scanId || "—"}</dd>
                <dt>Start Time</dt>
                <dd>{details.start ? fmtTime(details.start) : "—"}</dd>
                <dt>End Time</dt>
                <dd>{details.end ? fmtTime(details.end) : "—"}</dd>
                <dt>Duration</dt>
                <dd>{details.start && details.end ? fmtDuration(durationMs(details.start, details.end)) : "—"}</dd>
                <dt>Source</dt>
                <dd>{details.source}</dd>
                <dt>Status</dt>
                <dd className="row" style={{ gap: 6 }}>
                  <CheckIcon size={14} className="ok-ico" /> Succeeded
                </dd>
              </dl>
              <div className="metrics">
                <div className="metric ok">
                  <div className="metric-top">
                    <span>Compliant</span>
                    <span className="n">
                      {details.compliant} <span className="faint">({pct(details.compliant)}%)</span>
                    </span>
                  </div>
                  <div className="metric-bar">
                    <span style={{ width: `${pct(details.compliant)}%` }} />
                  </div>
                </div>
                <div className="metric bad">
                  <div className="metric-top">
                    <span>Noncompliant</span>
                    <span className="n">
                      {details.violations} <span className="faint">({pct(details.violations)}%)</span>
                    </span>
                  </div>
                  <div className="metric-bar">
                    <span style={{ width: `${pct(details.violations)}%` }} />
                  </div>
                </div>
                <div className="faint" style={{ fontSize: 12 }}>{details.evaluated} resources evaluated</div>
              </div>
            </div>
          ) : (
            <div className="collapsed-rail">
              <button title="Show scan details" onClick={() => setPaneOpen(true)}>
                <ChevronIcon size={16} />
              </button>
            </div>
          )}
        </div>
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
            {sortedHistory.length} of {history.length}
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
        ) : sortedHistory.length === 0 ? (
          <div className="empty">No scans match the filter.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <SortTh label="Start Time" field="started_at" sort={histSort} />
                  <SortTh label="Duration" field="duration" sort={histSort} />
                  <SortTh label="Source" field="source" sort={histSort} />
                  <SortTh label="Evaluated" field="evaluated" sort={histSort} />
                  <SortTh label="Violations" field="violations" sort={histSort} />
                </tr>
              </thead>
              <tbody>
                {sortedHistory.map((h) => (
                  <tr key={h.scan_id}>
                    <td>
                      <button className="linkbtn" onClick={() => viewScan(h, h.scan_id)}>
                        {fmtTime(h.started_at)}
                      </button>
                    </td>
                    <td>{fmtDuration(durationMs(h.started_at, h.finished_at))}</td>
                    <td>{h.triggered_by}</td>
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
