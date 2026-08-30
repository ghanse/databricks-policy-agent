import { useEffect, useState } from "react";
import { api } from "../api";
import type { Settings } from "../types";
import type { Theme } from "../theme";
import { useToast } from "../toast";
import { CheckIcon, EditIcon, MoonIcon, PlusIcon, SunIcon, TrashIcon } from "./icons";

interface TagRow {
  key: string;
  value: string;
  editing: boolean;
}
interface EmailRow {
  value: string;
  editing: boolean;
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
  const [emails, setEmails] = useState<EmailRow[]>([]);
  const [webhook, setWebhook] = useState("");
  const [webhookEditing, setWebhookEditing] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (settings) {
      setTags(
        Object.entries(settings.storage.object_tags).map(([key, value]) => ({ key, value, editing: false })),
      );
      setEmails(settings.notifications.emails.map((value) => ({ value, editing: false })));
      setWebhook(settings.notifications.webhook ?? "");
    }
  }, [settings]);

  if (!settings) {
    return <div className="panel muted">Loading settings…</div>;
  }

  const persist = async (partial: Record<string, unknown>, ok: string, kind: "save" | "delete") => {
    try {
      const updated = await api.updateSettings(partial);
      onSaved(updated);
      toast.push(ok, kind);
    } catch (e) {
      toast.push(String(e), "error");
    }
  };

  const saveTags = (rows: TagRow[], kind: "save" | "delete") => {
    const obj: Record<string, string> = {};
    for (const r of rows) if (r.key.trim()) obj[r.key.trim()] = r.value.trim();
    return persist({ object_tags: obj }, kind === "delete" ? "Tag removed" : "Tags saved", kind);
  };
  const saveEmails = (rows: EmailRow[], kind: "save" | "delete") =>
    persist(
      { notification_emails: rows.map((e) => e.value.trim()).filter(Boolean) },
      kind === "delete" ? "Email removed" : "Emails saved",
      kind,
    );

  return (
    <>
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

      <div className="panel">
        <h3>Notifications</h3>
        {isAdmin ? (
          <>
            <label className="field">On-failure emails</label>
            <div className="stack" style={{ marginBottom: 14 }}>
              {emails.map((row, i) => (
                <div key={i} className="kv-row">
                  <input
                    placeholder="owner@example.com"
                    disabled={!row.editing}
                    value={row.value}
                    onChange={(e) =>
                      setEmails((list) => list.map((v, j) => (j === i ? { ...v, value: e.target.value } : v)))
                    }
                  />
                  {row.editing ? (
                    <button
                      className="icon-btn act-ok"
                      title="Save"
                      onClick={() => {
                        setEmails((list) => list.map((v, j) => (j === i ? { ...v, editing: false } : v)));
                        saveEmails(
                          emails.map((v, j) => (j === i ? { ...v, editing: false } : v)),
                          "save",
                        );
                      }}
                    >
                      <CheckIcon size={15} />
                    </button>
                  ) : (
                    <button
                      className="icon-btn act-neutral"
                      title="Edit"
                      onClick={() => setEmails((list) => list.map((v, j) => (j === i ? { ...v, editing: true } : v)))}
                    >
                      <EditIcon size={15} />
                    </button>
                  )}
                  <button
                    className="icon-btn act-danger"
                    title="Remove"
                    onClick={() => {
                      const next = emails.filter((_, j) => j !== i);
                      setEmails(next);
                      saveEmails(next, "delete");
                    }}
                  >
                    <TrashIcon size={15} />
                  </button>
                </div>
              ))}
              <div>
                <button
                  className="action secondary tiny"
                  onClick={() => setEmails((l) => [...l, { value: "", editing: true }])}
                >
                  <PlusIcon size={13} /> Add email
                </button>
              </div>
            </div>
            <label className="field">Webhook URL</label>
            <div className="kv-row">
              <input
                disabled={!webhookEditing}
                value={webhook}
                onChange={(e) => setWebhook(e.target.value)}
                placeholder="https://hooks.example/…"
              />
              {webhookEditing ? (
                <button
                  className="icon-btn act-ok"
                  title="Save"
                  onClick={() => {
                    setWebhookEditing(false);
                    persist({ notification_webhook: webhook.trim() }, "Webhook saved", "save");
                  }}
                >
                  <CheckIcon size={15} />
                </button>
              ) : (
                <button className="icon-btn act-neutral" title="Edit" onClick={() => setWebhookEditing(true)}>
                  <EditIcon size={15} />
                </button>
              )}
              <button
                className="icon-btn act-danger"
                title="Remove"
                onClick={() => {
                  setWebhook("");
                  setWebhookEditing(false);
                  persist({ notification_webhook: "" }, "Webhook removed", "delete");
                }}
              >
                <TrashIcon size={15} />
              </button>
            </div>
          </>
        ) : (
          <p className="muted">
            Emails: {emails.map((e) => e.value).join(", ") || "none"} · Webhook:{" "}
            {settings.notifications.webhook_configured ? "configured" : "not configured"}
          </p>
        )}
      </div>

      <div className="panel">
        <h3>Object tags</h3>
        {isAdmin ? (
          <div className="stack">
            {tags.length > 0 && (
              <div className="kv-head">
                <span className="kv-h" style={{ flex: "1 1 auto" }}>Key</span>
                <span className="kv-h" style={{ flex: "1 1 auto" }}>Value</span>
                <span style={{ width: 72, flex: "none" }} />
              </div>
            )}
            {tags.map((row, i) => (
              <div key={i} className="kv-row">
                <input
                  placeholder="key"
                  disabled={!row.editing}
                  value={row.key}
                  onChange={(e) => setTags((t) => t.map((r, j) => (j === i ? { ...r, key: e.target.value } : r)))}
                />
                <input
                  placeholder="value"
                  disabled={!row.editing}
                  value={row.value}
                  onChange={(e) => setTags((t) => t.map((r, j) => (j === i ? { ...r, value: e.target.value } : r)))}
                />
                {row.editing ? (
                  <button
                    className="icon-btn act-ok"
                    title="Save"
                    onClick={() => {
                      const next = tags.map((r, j) => (j === i ? { ...r, editing: false } : r));
                      setTags(next);
                      saveTags(next, "save");
                    }}
                  >
                    <CheckIcon size={15} />
                  </button>
                ) : (
                  <button
                    className="icon-btn act-neutral"
                    title="Edit"
                    onClick={() => setTags((t) => t.map((r, j) => (j === i ? { ...r, editing: true } : r)))}
                  >
                    <EditIcon size={15} />
                  </button>
                )}
                <button
                  className="icon-btn act-danger"
                  title="Delete"
                  onClick={() => {
                    const next = tags.filter((_, j) => j !== i);
                    setTags(next);
                    saveTags(next, "delete");
                  }}
                >
                  <TrashIcon size={15} />
                </button>
              </div>
            ))}
            <div>
              <button
                className="action secondary tiny"
                onClick={() => setTags((t) => [...t, { key: "", value: "", editing: true }])}
              >
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
      </div>

      <div className="panel">
        <h3>Storage</h3>
        <div className="stack" style={{ maxWidth: 460 }}>
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
    </>
  );
}
