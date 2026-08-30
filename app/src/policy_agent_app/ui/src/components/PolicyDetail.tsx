import { useEffect, useState } from "react";
import { api } from "../api";
import type { Policy } from "../types";
import { effectLabel, resourceTypeLabel, severityLabel, statusLabel } from "../labels";

type View = "form" | "yaml";

/** A drawer that shows one policy either as readable fields or as OPA-style YAML. */
export function PolicyDetail({ name, onClose }: { name: string; onClose: () => void }) {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [yaml, setYaml] = useState<string>("");
  const [view, setView] = useState<View>("form");
  const [error, setError] = useState("");

  useEffect(() => {
    api.getPolicy(name).then(setPolicy).catch((e) => setError(String(e)));
    api.getPolicyYaml(name).then((r) => setYaml(r.yaml)).catch(() => setYaml(""));
  }, [name]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="spread" style={{ marginBottom: 14 }}>
          <div>
            <h3 style={{ fontSize: 16 }}>{name}</h3>
            {policy && <div className="faint" style={{ fontSize: 12 }}>version {policy.version}</div>}
          </div>
          <div className="row">
            <div className="toggle">
              <button className={view === "form" ? "on" : ""} onClick={() => setView("form")}>
                Fields
              </button>
              <button className={view === "yaml" ? "on" : ""} onClick={() => setView("yaml")}>
                YAML
              </button>
            </div>
            <button className="action secondary tiny" onClick={onClose}>
              Close
            </button>
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        {view === "yaml" ? (
          <pre className="yaml">{yaml || "…"}</pre>
        ) : policy ? (
          <div className="detail">
            <Field label="Status" value={statusLabel(policy.status)} />
            <Field label="Resource type" value={resourceTypeLabel(policy.resource_type)} />
            <Field label="Effect" value={effectLabel(policy.effect)} />
            <Field label="Severity" value={severityLabel(policy.severity)} />
            {policy.description && <Field label="Description" value={policy.description} wide />}
            {policy.remediation && <Field label="Recommended action" value={policy.remediation} wide />}
            <div className="detail-block">
              <div className="field-label">Rule</div>
              <pre className="yaml">{JSON.stringify(policy.rule, null, 2)}</pre>
            </div>
            {policy.match && (
              <div className="detail-block">
                <div className="field-label">Match selector</div>
                <pre className="yaml">{JSON.stringify(policy.match, null, 2)}</pre>
              </div>
            )}
          </div>
        ) : (
          <div className="muted">Loading…</div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={`detail-block ${wide ? "wide" : ""}`}>
      <div className="field-label">{label}</div>
      <div>{value}</div>
    </div>
  );
}
