import { useEffect, useState } from "react";
import { api } from "../api";
import type { Policy } from "../types";
import { effectLabel, resourceTypeLabel, severityLabel, statusLabel } from "../labels";
import { useToast, type ToastKind } from "../toast";
import { transitionsFor } from "../policyActions";
import { highlightJson, highlightYaml } from "../highlight";
import { ArrowLeftIcon, CodeIcon, ListIcon, TrashIcon } from "./icons";
import { NoteDialog, type NoteRequest } from "./NoteDialog";

type View = "fields" | "yaml";

/** Full-page policy view (replaces the old modal): read-only fields, a YAML view, and the
 *  approval actions available for the policy's current status. */
export function PolicyPage({
  name,
  isAdmin,
  onBack,
  onChanged,
}: {
  name: string;
  isAdmin: boolean;
  onBack: () => void;
  onChanged: () => void;
}) {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [yaml, setYaml] = useState("");
  const [view, setView] = useState<View>("fields");
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState<NoteRequest | null>(null);
  const toast = useToast();

  const load = () => {
    api.getPolicy(name).then(setPolicy).catch((e) => setError(String(e)));
    api.getPolicyYaml(name).then((r) => setYaml(r.yaml)).catch(() => setYaml(""));
  };
  useEffect(load, [name]);

  const runTransition = (action: string, label: string, kind: ToastKind) => {
    setError("");
    setDialog({
      title: `${label} — ${name}`,
      description: "This is recorded as an immutable approval event.",
      confirmLabel: label,
      onConfirm: async (note) => {
        try {
          await api.transition(name, action, note);
          toast.push(`${label} ✓`, kind);
          load();
          onChanged();
        } catch (e) {
          toast.push(String(e), "error");
        }
      },
    });
  };

  const remove = () => {
    setDialog({
      title: `Delete ${name}?`,
      description: "This permanently removes the policy.",
      confirmLabel: "Delete",
      onConfirm: async () => {
        try {
          await api.deletePolicy(name);
          toast.push("Policy deleted", "delete");
          onChanged();
          onBack();
        } catch (e) {
          toast.push(String(e), "error");
        }
      },
    });
  };

  return (
    <>
      <button className="backlink" onClick={onBack}>
        <ArrowLeftIcon size={15} /> All policies
      </button>

      <div className="panel">
        <div className="spread" style={{ marginBottom: 16 }}>
          <div>
            <h2 style={{ fontSize: 19 }}>{name}</h2>
            {policy && (
              <div className="row" style={{ gap: 8, marginTop: 6 }}>
                <span className={`badge ${policy.status}`}>{statusLabel(policy.status)}</span>
                <span className="faint" style={{ fontSize: 12 }}>version {policy.version}</span>
              </div>
            )}
          </div>
          <div className="toggle">
            <button className={view === "fields" ? "on" : ""} onClick={() => setView("fields")}>
              <ListIcon size={14} /> Fields
            </button>
            <button className={view === "yaml" ? "on" : ""} onClick={() => setView("yaml")}>
              <CodeIcon size={14} /> YAML
            </button>
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        {view === "yaml" ? (
          <pre className="code">{highlightYaml(yaml || "…")}</pre>
        ) : policy ? (
          <>
            <div className="form-grid">
              <ReadField label="Resource type" value={resourceTypeLabel(policy.resource_type)} />
              <ReadField label="Effect" value={effectLabel(policy.effect)} />
              <ReadField label="Severity" value={severityLabel(policy.severity)} />
              <ReadField label="Status" value={statusLabel(policy.status)} />
            </div>
            <div style={{ marginTop: 14 }}>
              <ReadField label="Description" value={policy.description || "—"} />
            </div>
            <div style={{ marginTop: 14 }}>
              <ReadField label="Recommended action" value={policy.remediation || "—"} />
            </div>
            <label className="field" style={{ marginTop: 16 }}>
              Rule
            </label>
            <pre className="code wide">{highlightJson(JSON.stringify(policy.rule, null, 2))}</pre>
            {policy.match && (
              <>
                <label className="field" style={{ marginTop: 14 }}>
                  Match selector
                </label>
                <pre className="code wide">{highlightJson(JSON.stringify(policy.match, null, 2))}</pre>
              </>
            )}
          </>
        ) : (
          <div className="muted">Loading…</div>
        )}

        {policy && (
          <div className="row wrap" style={{ marginTop: 18, gap: 8 }}>
            {transitionsFor(policy.status).map((t) => {
              const Icon = t.icon;
              return (
                <button
                  key={t.action}
                  className="action secondary"
                  onClick={() => runTransition(t.action, t.label, t.kind)}
                >
                  <Icon size={14} /> {t.label}
                </button>
              );
            })}
            {isAdmin && (
              <button className="action secondary danger-btn" onClick={remove}>
                <TrashIcon size={14} /> Delete
              </button>
            )}
          </div>
        )}
      </div>
      <NoteDialog request={dialog} onClose={() => setDialog(null)} />
    </>
  );
}

function ReadField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="field">{label}</label>
      <input disabled value={value} />
    </div>
  );
}
