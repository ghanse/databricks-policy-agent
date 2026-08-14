import { useEffect, useState } from "react";
import { api } from "./api";
import type { MyRoles, Settings } from "./types";
import { PoliciesTab } from "./components/PoliciesTab";
import { ApprovalsTab } from "./components/ApprovalsTab";
import { ScansTab } from "./components/ScansTab";
import { RemediationsTab } from "./components/RemediationsTab";
import { SettingsTab } from "./components/SettingsTab";

const TABS = ["Policies", "Approvals", "Scans", "Remediations", "Settings"] as const;
type Tab = (typeof TABS)[number];

export function App() {
  const [tab, setTab] = useState<Tab>("Policies");
  const [roles, setRoles] = useState<MyRoles | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);

  useEffect(() => {
    api.getMyRoles().then(setRoles).catch(() => setRoles(null));
    api.getSettings().then(setSettings).catch(() => setSettings(null));
  }, []);

  return (
    <>
      <header>
        <h1>Databricks Policy Agent</h1>
        <span className="user">
          {roles ? `${roles.user} — ${roles.roles.join(", ") || "no roles"}` : ""}
        </span>
      </header>
      <nav>
        {TABS.map((name) => (
          <button
            key={name}
            className={name === tab ? "active" : ""}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </nav>
      <main>
        {tab === "Policies" && <PoliciesTab settings={settings} />}
        {tab === "Approvals" && <ApprovalsTab />}
        {tab === "Scans" && <ScansTab settings={settings} />}
        {tab === "Remediations" && <RemediationsTab />}
        {tab === "Settings" && <SettingsTab settings={settings} />}
      </main>
    </>
  );
}
