import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Finding, ScanHeader, ScanResult, Settings } from "../types";
import { resourceTypeLabel, enforcementLabel } from "../labels";
import { useToast } from "../toast";
import { useSort, SortTh, ENFORCEMENT_RANK } from "../useSort";
import { usePage, PagerBar } from "../usePage";
import { resourceUrl } from "../resourceUrl";
import { ExternalIcon, LightbulbIcon } from "./icons";
import { SplitButton } from "./SplitButton";
import { FilterBar } from "./FilterBar";
import { Select } from "./Select";
import { DateRangePicker, type DateRange } from "./DateRangePicker";
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
  const [viewing, setViewing] = useState<
    { header: ScanHeader | null; findings: Finding[]; scanId: string } | null
  >(null);
  const [history, setHistory] = useState<ScanHeader[]>([]);
  const [running, setRunning] = useState(false);
  const [search, setSearch] = useState("");
  const [fEnforcement, setFEnforcement] = useState("");
  const [fType, setFType] = useState("");
  const [fSource, setFSource] = useState("");
  const [startRange, setStartRange] = useState<DateRange>({ from: "", to: "" });
  const [endRange, setEndRange] = useState<DateRange>({ from: "", to: "" });
  const toast = useToast();
  const histSort = useSort<ScanHeader>("started_at");
  const violSort = useSort<Finding>("enforcement_level");

  const loadHistory = () => api.listScans().then(setHistory).catch(() => setHistory([]));
  useEffect(() => {
    loadHistory();
  }, []);

  const viewScan = async (header: ScanHeader | null, scanId: string) => {
    try {
      const findings = await api.scanFindings(scanId);
      setResult(null);
      setViewing({ header, findings, scanId });
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

  // If a scan was opened before its history row loaded (e.g. via a remediation link),
  // backfill the header once history arrives so the details pane shows its metadata.
  useEffect(() => {
    setViewing((v) => {
      if (v && !v.header) {
        const header = history.find((h) => h.scan_id === v.scanId);
        if (header) return { ...v, header };
      }
      return v;
    });
  }, [history]);

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
        ? { scanId: viewing.scanId, start: "", end: "", source: "—", evaluated: 0, compliant: 0, violations: 0 }
        : null;

  const resourceTypes = settings?.resource_types ?? [];
  const workspaceUrl = settings?.workspace_url ?? "";
  const sources = useMemo(() => [...new Set(history.map((h) => h.triggered_by))], [history]);

  const filteredViolations = useMemo(() => {
    const q = search.toLowerCase();
    return violations.filter(
      (f) =>
        (!q || f.policy_name.toLowerCase().includes(q) || (f.resource_name ?? "").toLowerCase().includes(q)) &&
        (!fEnforcement || f.enforcement_level === fEnforcement) &&
        (!fType || f.resource_type === fType),
    );
  }, [violations, search, fEnforcement, fType]);
  const sortedViolations = violSort.apply(filteredViolations, {
    enforcement_level: (f) => ENFORCEMENT_RANK[f.enforcement_level] ?? -1,
    policy: (f) => f.policy_name.toLowerCase(),
    type: (f) => f.resource_type,
    resource: (f) => (f.resource_name ?? "").toLowerCase(),
  });
  const violPager = usePage(sortedViolations, 10);

  const filteredHistory = useMemo(() => {
    const inRange = (iso: string, r: DateRange) => {
      if (!r.from && !r.to) return true;
      const t = new Date(iso).getTime();
      if (r.from && t < new Date(`${r.from}T00:00:00`).getTime()) return false;
      if (r.to && t > new Date(`${r.to}T23:59:59`).getTime()) return false;
      return true;
    };
    return history.filter(
      (h) =>
        (!fSource || h.triggered_by === fSource) &&
        inRange(h.started_at, startRange) &&
        inRange(h.finished_at, endRange),
    );
  }, [history, fSource, startRange, endRange]);
  const sortedHistory = histSort.apply(filteredHistory, {
    started_at: (h) => new Date(h.started_at).getTime(),
    duration: (h) => durationMs(h.started_at, h.finished_at),
    source: (h) => h.triggered_by,
    evaluated: (h) => Number(h.evaluated),
    compliant: (h) => Number(h.compliant),
    violations: (h) => Number(h.violations),
  });
  const histPager = usePage(sortedHistory, 10);

  // ---- Result page ----
  if (mode === "result" && details) {
    const pct = (n: number) => (details.evaluated > 0 ? Math.round((n / details.evaluated) * 100) : 0);
    return (
      <>
        <div className="crumbs">
          <button onClick={() => setMode("list")}>Scans</button>
          <span className="sep">/</span>
          <span className="here">{details.start ? fmtTime(details.start) : "Scan result"}</span>
        </div>

        <div className="panel">
          <h3>Scan details</h3>
          <div className="detail-grid">
            <Field label="Scan ID" value={details.scanId || "—"} mono />
            <Field label="Start Time" value={details.start ? fmtTime(details.start) : "—"} />
            <Field label="End Time" value={details.end ? fmtTime(details.end) : "—"} />
            <Field
              label="Duration"
              value={details.start && details.end ? fmtDuration(durationMs(details.start, details.end)) : "—"}
            />
            <Field label="Source" value={details.source} mono />
            <div className="df">
              <span className="df-k">Status</span>
              <span className="df-v">
                <span className="badge succeeded">Succeeded</span>
              </span>
            </div>
          </div>
          <div className="metrics-h">
            <div className="metric ok">
              <div className="metric-top">
                <span>Compliant</span>
                <span className="n">
                  {details.compliant} of {details.evaluated}{" "}
                  <span className="faint">({pct(details.compliant)}%)</span>
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
                  {details.violations} of {details.evaluated}{" "}
                  <span className="faint">({pct(details.violations)}%)</span>
                </span>
              </div>
              <div className="metric-bar">
                <span style={{ width: `${pct(details.violations)}%` }} />
              </div>
            </div>
          </div>
        </div>

        <div className="panel">
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
                label: "Enforcement",
                value: fEnforcement,
                onChange: setFEnforcement,
                options: ["advisory", "soft", "hard"].map((s) => ({ value: s, label: enforcementLabel(s) })),
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
            <>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <SortTh label="Enforcement" field="enforcement_level" sort={violSort} />
                      <SortTh label="Policy" field="policy" sort={violSort} />
                      <SortTh label="Type" field="type" sort={violSort} />
                      <SortTh label="Resource" field="resource" sort={violSort} />
                      <th>Recommended fix</th>
                    </tr>
                  </thead>
                  <tbody>
                    {violPager.pageRows.map((f, i) => {
                      const url = resourceUrl(workspaceUrl, f.resource_type, f.resource_id);
                      return (
                        <tr key={i}>
                          <td>
                            <span className={`badge ${f.enforcement_level}`}>{enforcementLabel(f.enforcement_level)}</span>
                          </td>
                          <td>
                            {f.policy_name}
                            <div className="faint">{f.message}</div>
                          </td>
                          <td>
                            <span className="badge neutral">{resourceTypeLabel(f.resource_type)}</span>
                          </td>
                          <td>
                            {url ? (
                              <a className="reslink" href={url} target="_blank" rel="noreferrer">
                                {f.resource_name} <ExternalIcon size={12} />
                              </a>
                            ) : (
                              f.resource_name
                            )}
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
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <PagerBar pager={violPager} />
            </>
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
          Scans
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
            <span>Start time</span>
            <DateRangePicker value={startRange} onChange={setStartRange} />
          </label>
          <label className="filter">
            <span>End time</span>
            <DateRangePicker value={endRange} onChange={setEndRange} />
          </label>
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
                  <SortTh label="Compliant" field="compliant" sort={histSort} />
                  <SortTh label="Violations" field="violations" sort={histSort} />
                </tr>
              </thead>
              <tbody>
                {histPager.pageRows.map((h) => (
                  <tr key={h.scan_id}>
                    <td>
                      <button className="linkbtn" onClick={() => viewScan(h, h.scan_id)}>
                        {fmtTime(h.started_at)}
                      </button>
                    </td>
                    <td>{fmtDuration(durationMs(h.started_at, h.finished_at))}</td>
                    <td>{h.triggered_by}</td>
                    <td>
                      <span className="badge neutral">{h.evaluated}</span>
                    </td>
                    <td>
                      <span className="badge succeeded">{h.compliant}</span>
                    </td>
                    <td>{Number(h.violations) > 0 ? <span className="badge high">{h.violations}</span> : "0"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <PagerBar pager={histPager} />
          </div>
        )}
      </div>
    </>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="df">
      <span className="df-k">{label}</span>
      <span className={`df-v ${mono ? "mono" : ""}`}>{value}</span>
    </div>
  );
}
