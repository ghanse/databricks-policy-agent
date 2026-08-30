import { useEffect, useState } from "react";
import { api } from "../api";
import type { Settings } from "../types";

function tagsToText(tags: Record<string, string>): string {
  return Object.entries(tags)
    .map(([k, v]) => `${k}=${v}`)
    .join(", ");
}

function parseTags(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const pair of text.split(",")) {
    const [k, ...rest] = pair.split("=");
    const key = k.trim();
    if (key) out[key] = rest.join("=").trim();
  }
  return out;
}

export function SettingsTab({
  settings,
  isAdmin,
  onSaved,
}: {
  settings: Settings | null;
  isAdmin: boolean;
  onSaved: (s: Settings) => void;
}) {
  const [tags, setTags] = useState("");
  const [emails, setEmails] = useState("");
  const [webhook, setWebhook] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setTags(tagsToText(settings.storage.object_tags));
      setEmails(settings.notifications.emails.join(", "));
      setWebhook(settings.notifications.webhook ?? "");
    }
  }, [settings]);

  if (!settings) {
    return <div className="panel muted">Loading settings…</div>;
  }

  const save = async () => {
    setError("");
    setStatus("");
    setSaving(true);
    try {
      const updated = await api.updateSettings({
        object_tags: parseTags(tags),
        notification_emails: emails
          .split(",")
          .map((e) => e.trim())
          .filter(Boolean),
        notification_webhook: webhook.trim(),
      });
      onSaved(updated);
      setStatus("Saved ✓");
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="panel">
        <h3>
          Storage
          <span className="hint">fixed at deploy time</span>
        </h3>
        <table>
          <tbody>
            <tr>
              <th style={{ width: 160 }}>Backend</th>
              <td>{settings.storage.backend === "uc" ? "Unity Catalog (Delta)" : settings.storage.backend}</td>
            </tr>
            <tr>
              <th>Schema</th>
              <td className="mono">{settings.storage.qualified_schema}</td>
            </tr>
          </tbody>
        </table>
        <p className="faint" style={{ fontSize: 12, marginBottom: 0 }}>
          The storage backend and schema are set by the deployment bundle and can't be changed here —
          changing where state lives would separate the app from its existing data.
        </p>
      </div>

      <div className="panel">
        <h3>
          Object tags
          {!isAdmin && <span className="hint">admins only</span>}
        </h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Stamped on every object the agent creates and on each stored row. A{" "}
          <code>managed_by=policy-agent</code> marker is always kept.
        </p>
        {isAdmin ? (
          <>
            <label className="field">Tags (key=value, comma-separated)</label>
            <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="team=platform, environment=dev" />
          </>
        ) : (
          <div className="row wrap">
            {Object.entries(settings.storage.object_tags).map(([k, v]) => (
              <span key={k} className="badge pill-outline">
                {k}={v}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="panel">
        <h3>
          Notifications
          {!isAdmin && <span className="hint">admins only</span>}
        </h3>
        {isAdmin ? (
          <>
            <label className="field">On-failure emails (comma-separated)</label>
            <input
              value={emails}
              onChange={(e) => setEmails(e.target.value)}
              placeholder="team@example.com, oncall@example.com"
              style={{ marginBottom: 12 }}
            />
            <label className="field">Webhook URL</label>
            <input value={webhook} onChange={(e) => setWebhook(e.target.value)} placeholder="https://hooks.example/…" />
          </>
        ) : (
          <p className="muted">
            Emails: {settings.notifications.emails.join(", ") || "none"} · Webhook:{" "}
            {settings.notifications.webhook_configured ? "configured" : "not configured"}
          </p>
        )}
        {isAdmin && (
          <div className="row" style={{ marginTop: 14 }}>
            <button className="action" onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save settings"}
            </button>
            <span className="muted">{status}</span>
            {error && <span className="error" style={{ margin: 0 }}>{error}</span>}
          </div>
        )}
        <p className="faint" style={{ fontSize: 12, marginBottom: 0, marginTop: 12 }}>
          Applies to app-initiated scans and writes. Scheduled scan jobs use the destinations set in
          the deployment bundle until they are redeployed.
        </p>
      </div>
    </>
  );
}
