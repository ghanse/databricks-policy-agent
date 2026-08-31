import { useEffect, useState } from "react";
import { api } from "./api";
import type { MyRoles, Settings } from "./types";
import { applyTheme, initialTheme, type Theme } from "./theme";
import { PoliciesTab } from "./components/PoliciesTab";
import { ScansTab } from "./components/ScansTab";
import { RemediationsTab } from "./components/RemediationsTab";
import { SettingsTab } from "./components/SettingsTab";
import { ProfileMenu } from "./components/ProfileMenu";
import { PolicyIcon, RemediationIcon, ScanIcon, SettingsIcon } from "./components/icons";

type IconType = (props: { className?: string; size?: number }) => JSX.Element;

interface Section {
  key: string;
  label: string;
  icon: IconType;
}

const SECTIONS: Section[] = [
  { key: "Policies", label: "Policies", icon: PolicyIcon },
  { key: "Scans", label: "Scans", icon: ScanIcon },
  { key: "Remediations", label: "Remediations", icon: RemediationIcon },
  { key: "Settings", label: "Settings", icon: SettingsIcon },
];

export function App() {
  const [active, setActive] = useState("Policies");
  const [roles, setRoles] = useState<MyRoles | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [focusScanId, setFocusScanId] = useState<string | null>(null);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    api.getMyRoles().then(setRoles).catch(() => setRoles(null));
    api.getSettings().then(setSettings).catch(() => setSettings(null));
  }, []);

  const openScan = (scanId: string) => {
    setFocusScanId(scanId);
    setActive("Scans");
  };

  const section = SECTIONS.find((s) => s.key === active)!;
  const isAdmin = roles?.roles.includes("admin") ?? false;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="mark">
            <PolicyIcon size={19} />
          </div>
          <div>
            <div className="name">Databricks Policy Agent</div>
            {settings?.workspace_id && <div className="sub">Workspace ID: {settings.workspace_id}</div>}
          </div>
        </div>

        <div className="nav-section">Workspace</div>
        {SECTIONS.filter((s) => s.key !== "Settings").map((s) => {
          const Icon = s.icon;
          return (
            <button
              key={s.key}
              className={`nav-item ${s.key === active ? "active" : ""}`}
              onClick={() => setActive(s.key)}
            >
              <Icon className="ico" size={17} />
              {s.label}
            </button>
          );
        })}

        <div className="spacer" />
        <ProfileMenu roles={roles} onOpenSettings={() => setActive("Settings")} />
      </aside>

      <div className="content">
        <div className="topbar">
          <h2>{section.label}</h2>
        </div>
        <main>
          {active === "Policies" && <PoliciesTab settings={settings} isAdmin={isAdmin} />}
          {active === "Scans" && (
            <ScansTab settings={settings} focusScanId={focusScanId} onFocusHandled={() => setFocusScanId(null)} />
          )}
          {active === "Remediations" && (
            <RemediationsTab onOpenScan={openScan} workspaceUrl={settings?.workspace_url ?? ""} />
          )}
          {active === "Settings" && (
            <SettingsTab
              settings={settings}
              isAdmin={isAdmin}
              onSaved={(s) => setSettings(s)}
              theme={theme}
              onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            />
          )}
        </main>
      </div>
    </div>
  );
}
