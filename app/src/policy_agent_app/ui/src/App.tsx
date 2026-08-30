import { useEffect, useState } from "react";
import { api } from "./api";
import type { MyRoles, Settings } from "./types";
import { PoliciesTab } from "./components/PoliciesTab";
import { ApprovalsTab } from "./components/ApprovalsTab";
import { ScansTab } from "./components/ScansTab";
import { RemediationsTab } from "./components/RemediationsTab";
import { SettingsTab } from "./components/SettingsTab";
import { ProfileMenu } from "./components/ProfileMenu";
import {
  ApprovalIcon,
  PolicyIcon,
  RemediationIcon,
  ScanIcon,
  SettingsIcon,
} from "./components/icons";

type IconType = (props: { className?: string; size?: number }) => JSX.Element;

interface Section {
  key: string;
  label: string;
  icon: IconType;
  description: string;
}

const SECTIONS: Section[] = [
  {
    key: "Policies",
    label: "Policies",
    icon: PolicyIcon,
    description: "Author allow/deny policies and manage the ones already in place.",
  },
  {
    key: "Approvals",
    label: "Approvals",
    icon: ApprovalIcon,
    description: "Move policies through the draft → review → approved workflow. Only approved policies are scanned.",
  },
  {
    key: "Scans",
    label: "Scans",
    icon: ScanIcon,
    description: "Run a compliance scan across the workspace and inspect the violations it finds.",
  },
  {
    key: "Remediations",
    label: "Remediations",
    icon: RemediationIcon,
    description: "Track each violation to resolution, with the recommended fix and an owner.",
  },
  {
    key: "Settings",
    label: "Settings",
    icon: SettingsIcon,
    description: "Storage backend, notification targets, and the vocabulary the agent understands.",
  },
];

export function App() {
  const [active, setActive] = useState("Policies");
  const [roles, setRoles] = useState<MyRoles | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [policyCount, setPolicyCount] = useState<number | null>(null);
  const [openCount, setOpenCount] = useState<number | null>(null);

  useEffect(() => {
    api.getMyRoles().then(setRoles).catch(() => setRoles(null));
    api.getSettings().then(setSettings).catch(() => setSettings(null));
    api.listPolicies().then((p) => setPolicyCount(p.length)).catch(() => setPolicyCount(null));
    api
      .listRemediations()
      .then((r) => setOpenCount(r.filter((i) => i.status === "open" || i.status === "in_progress").length))
      .catch(() => setOpenCount(null));
  }, []);

  const section = SECTIONS.find((s) => s.key === active)!;
  const counts: Record<string, number | null> = { Policies: policyCount, Remediations: openCount };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="mark">P</div>
          <div>
            <div className="name">Policy Agent</div>
            <div className="sub">Databricks compliance</div>
          </div>
        </div>

        <div className="nav-section">Workspace</div>
        {SECTIONS.filter((s) => s.key !== "Settings").map((s) => {
          const Icon = s.icon;
          const count = counts[s.key];
          return (
            <button
              key={s.key}
              className={`nav-item ${s.key === active ? "active" : ""}`}
              onClick={() => setActive(s.key)}
            >
              <Icon className="ico" size={17} />
              {s.label}
              {count != null && count > 0 && <span className="count">{count}</span>}
            </button>
          );
        })}

        <div className="spacer" />
        <ProfileMenu roles={roles} onOpenSettings={() => setActive("Settings")} />
      </aside>

      <div className="content">
        <div className="topbar">
          <h2>{section.label}</h2>
          <div className="desc">{section.description}</div>
        </div>
        <main>
          {active === "Policies" && <PoliciesTab settings={settings} />}
          {active === "Approvals" && <ApprovalsTab />}
          {active === "Scans" && <ScansTab settings={settings} />}
          {active === "Remediations" && <RemediationsTab />}
          {active === "Settings" && <SettingsTab settings={settings} />}
        </main>
      </div>
    </div>
  );
}
