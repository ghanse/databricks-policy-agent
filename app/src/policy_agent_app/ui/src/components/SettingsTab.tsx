import type { Settings } from "../types";

export function SettingsTab({ settings }: { settings: Settings | null }) {
  if (!settings) {
    return <div className="panel muted">Loading settings…</div>;
  }
  return (
    <>
      <div className="panel">
        <h3>Storage</h3>
        <table>
          <tbody>
            <tr>
              <th>Backend</th>
              <td>{settings.storage.backend}</td>
            </tr>
            <tr>
              <th>Schema</th>
              <td>{settings.storage.qualified_schema}</td>
            </tr>
            <tr>
              <th>Object tags</th>
              <td>
                {Object.entries(settings.storage.object_tags)
                  .map(([k, v]) => `${k}=${v}`)
                  .join(", ") || "none"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h3>Vocabulary</h3>
        <p>
          <strong>Resource types:</strong> {settings.resource_types.join(", ")}
        </p>
        <p>
          <strong>Operators:</strong> {settings.operators.join(", ")}
        </p>
        <p>
          <strong>Roles:</strong> {settings.roles.join(", ")}
        </p>
      </div>
      <div className="panel">
        <h3>Notifications</h3>
        <p className="muted">
          Emails: {settings.notifications.emails.join(", ") || "none"} · Webhook:{" "}
          {settings.notifications.webhook_configured ? "configured" : "not configured"}
        </p>
      </div>
    </>
  );
}
