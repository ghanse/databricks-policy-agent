/** Human-readable labels for backend enum values, so the UI never shows raw
 *  identifiers like "sql_warehouse" or "in_review". */

const RESOURCE_TYPES: Record<string, string> = {
  job: "Job",
  cluster: "Cluster",
  sql_warehouse: "SQL Warehouse",
  app: "App",
  serving_endpoint: "Serving Endpoint",
};

const STATUSES: Record<string, string> = {
  draft: "Draft",
  in_review: "In review",
  approved: "Approved",
  rejected: "Rejected",
  archived: "Archived",
  open: "Open",
  in_progress: "In progress",
  resolved: "Resolved",
  waived: "Waived",
};

function titleCase(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

export function resourceTypeLabel(value: string): string {
  return RESOURCE_TYPES[value] ?? titleCase(value);
}

export function statusLabel(value: string): string {
  return STATUSES[value] ?? titleCase(value);
}

export function enforcementLabel(value: string): string {
  return titleCase(value);
}

export function effectLabel(value: string): string {
  return titleCase(value);
}

/** Generic humanizer for any remaining snake_case attribute. */
export function humanize(value: string): string {
  return titleCase(value);
}

/** Derive a display name from an email, e.g. "gregory.hansen@x.com" -> "Gregory Hansen". */
export function displayName(user: string): string {
  const local = user.split("@")[0] || user;
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (!parts.length) return user;
  return parts.map((p) => p[0].toUpperCase() + p.slice(1)).join(" ");
}
