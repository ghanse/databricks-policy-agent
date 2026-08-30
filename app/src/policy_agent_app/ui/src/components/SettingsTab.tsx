import { useEffect, useState } from "react";
import { api } from "../api";
import type { Settings } from "../types";
import type { Theme } from "../theme";
import { CheckIcon, MoonIcon, PlusIcon, SunIcon, TrashIcon } from "./icons";

interface TagRow {
  key: string;
  value: string;
}

export function SettingsTab({
  settings,
  isAdmin,
  onSaved,
  theme,
  onToggleTheme,
}: {
  settings: Settings | null;
  isAdmin: boolean;
  onSaved: (s: Settings) => void;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  const [tags, setTags] = useState<TagRow[]>([]);
  const [emails, setEmails] = useState<string[]>([]);
  const [webhook, setWebhook] = useState("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    if (settings) {
      setTags(Object.entries(settings.storage.object_tags).map(([key, value]) => ({ key, value })));
      setEmails([...settings.notifications.emails]);
      setWebhook(settings.notifications.webhook ?? "");
    }
  }, [settings]);

  if (!settings) {
    return <div className="panel muted">Loading settings…</div>;
  }

  const persist = async (partial: Record<string, unknown>, ok: string) => {
    setError("");
    setNote("");
    try {
      const updated = await api.updateSettings(partial);
      onSaved(updated);
      setNote(ok);
    } catch (e) {
      setError(String(e));
    }
  };

  const saveTags = (rows: TagRow[]) => {
    const obj: Record<string, string> = {};
    for (const r of rows) if (r.key.trim()) obj[r.key.trim()] = r.value.trim();
    return persist({ object_tags: obj }, "Tags saved ✓");
  };
  const saveEmails = (list: string[]) =>
    persist({ notification_emails: list.map((e) => e.trim()).filter(Boolean) }, "Emails saved ✓");

  return (
    <>
      <div className="panel">
        <h3>Storage</h3>
        <div className="form-grid">
          <div>
            <label className="field">Backend</label>
            <input
              disabled
              value={settings.storage.backend === "uc" ? "Unity Catalog (Delta)" : settings.storage.backend}
            />
          </div>
          <div>
            <label className="field">Schema</label>
            <input disabled value={settings.storage.qualified_schema} />
          </div>
        </div>
      </div>

      <div className="panel">
        <h3>Object tags</h3>
        {error && <div className="error">{error}</div>}
        {isAdmin ? (
          <div className="stack">
            {tags.map((row, i) => (
              <div key={i} className="kv-row">
                <input
                  placeholder="key"
                  value={row.key}
                  onChange={(e) =>
                    setTags((t) => t.map((r, j) => (j === i ? { ...r, key: e.target.value } : r)))
                  }
                />
                <span className="kv-eq">=</span>
                <input
                  placeholder="value"
                  value={row.value}
                  onChange={(e) =>
                    setTags((t) => t.map((r, j) => (j === i ? { ...r, value: e.target.value } : r)))
                  }
                />
                <button className="icon-btn ok" title="Save" onClick={() => saveTags(tags)}>
                  <CheckIcon size={15} />
                </button>
                <button
                  className="icon-btn danger"
                  title="Delete"
                  onClick={() => {
                    const next = tags.filter((_, j) => j !== i);
                    setTags(next);
                    saveTags(next);
                  }}
                >
                  <TrashIcon size={15} />
                </button>
              </div>
            ))}
            <div>
              <button className="action secondary tiny" onClick={() => setTags((t) => [...t, { key: "", value: "" }])}>
                <PlusIcon size={13} /> Add tag
              </button>
            </div>
          </div>
        ) : (
          <div className="row wrap">
            {tags.map((t) => (
              <span key={t.key} className="badge pill-outline">
                {t.key}={t.value}
              </span>
            ))}
          </div>
        )}
        {note && <div className="muted" style={{ marginTop: 8 }}>{note}</div>}
      </div>

      <div className="panel">
        <h3>Notifications</h3>
        {isAdmin ? (
          <>
            <label className="field">On-failure emails</label>
            <div className="stack" style={{ marginBottom: 14 }}>
              {emails.map((email, i) => (
                <div key={i} className="kv-row">
                  <input
                    placeholder="owner@example.com"
                    value={email}
                    onChange={(e) => setEmails((list) => list.map((v, j) => (j === i ? e.target.value : v)))}
                  />
                  <button className="icon-btn ok" title="Save" onClick={() => saveEmails(emails)}>
                    <CheckIcon size={15} />
                  </button>
                  <button
                    className="icon-btn danger"
                    title="Delete"
                    onClick={() => {
                      const next = emails.filter((_, j) => j !== i);
                      setEmails(next);
                      saveEmails(next);
                    }}
                  >
                    <TrashIcon size={15} />
                  </button>
                </div>
              ))}
              <div>
                <button className="action secondary tiny" onClick={() => setEmails((l) => [...l, ""])}>
                  <PlusIcon size={13} /> Add email
                </button>
              </div>
            </div>
            <label className="field">Webhook URL</label>
            <div className="kv-row">
              <input value={webhook} onChange={(e) => setWebhook(e.target.value)} placeholder="https://hooks.example/…" />
              <button
                className="icon-btn ok"
                title="Save"
                onClick={() => persist({ notification_webhook: webhook.trim() }, "Webhook saved ✓")}
              >
                <CheckIcon size={15} />
              </button>
            </div>
          </>
        ) : (
          <p className="muted">
            Emails: {emails.join(", ") || "none"} · Webhook:{" "}
            {settings.notifications.webhook_configured ? "configured" : "not configured"}
          </p>
        )}
      </div>

      <div className="panel">
        <h3>Appearance</h3>
        <div className="theme-toggle">
          <button className={theme === "light" ? "on" : ""} onClick={() => theme !== "light" && onToggleTheme()}>
            <SunIcon size={15} /> Light
          </button>
          <button className={theme === "dark" ? "on" : ""} onClick={() => theme !== "dark" && onToggleTheme()}>
            <MoonIcon size={15} /> Dark
          </button>
        </div>
      </div>
    </>
  );
}
