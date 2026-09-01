import { useEffect, useRef, useState } from "react";
import type { MyRoles } from "../types";
import { displayName, humanize } from "../labels";
import { ChevronIcon, SettingsIcon, UserIcon } from "./icons";

function initials(user: string): string {
  const local = user.split("@")[0];
  const parts = local.split(/[.\-_]/).filter(Boolean);
  const letters = parts.length >= 2 ? parts[0][0] + parts[1][0] : local.slice(0, 2);
  return letters.toUpperCase();
}

/** Top-left profile control: shows the signed-in user and opens a menu with their
 *  roles and a shortcut into Settings. */
export function ProfileMenu({ roles, onOpenSettings }: { roles: MyRoles | null; onOpenSettings: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const user = roles?.user ?? "Unknown user";
  const name = roles?.display_name || displayName(user);
  const userRoles = roles?.roles ?? [];

  return (
    <div className="profile" ref={ref}>
      <button className="profile-btn" onClick={() => setOpen((v) => !v)}>
        <span className="avatar">{initials(user)}</span>
        <span className="who">
          <div className="u">{name}</div>
          <div className="r">{userRoles.map(humanize).join(", ") || "no roles"}</div>
        </span>
        <ChevronIcon className="chev" size={15} />
      </button>
      {open && (
        <div className="menu">
          <div className="head">
            <div className="u">{name}</div>
            <div className="e">{user}</div>
          </div>
          <div className="role-chips">
            {userRoles.length ? (
              userRoles.map((r) => (
                <span key={r} className="badge pill-outline">
                  {humanize(r)}
                </span>
              ))
            ) : (
              <span className="faint" style={{ fontSize: 12 }}>
                No roles assigned
              </span>
            )}
          </div>
          <button
            className="menu-item"
            onClick={() => {
              onOpenSettings();
              setOpen(false);
            }}
          >
            <SettingsIcon className="ico" size={16} />
            Settings
          </button>
          <button className="menu-item" onClick={() => setOpen(false)}>
            <UserIcon className="ico" size={16} />
            Signed in via workspace SSO
          </button>
        </div>
      )}
    </div>
  );
}
