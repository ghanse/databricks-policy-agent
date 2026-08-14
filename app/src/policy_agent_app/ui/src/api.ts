import type {
  Finding,
  MyRoles,
  Policy,
  Remediation,
  ScanResult,
  Settings,
} from "./types";

const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(detail.detail ?? `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  getSettings: () => request<Settings>("/settings"),
  getMyRoles: () => request<MyRoles>("/roles/me"),

  listPolicies: (status?: string) =>
    request<Policy[]>(`/policies${status ? `?status=${status}` : ""}`),
  savePolicy: (body: unknown) =>
    request<Policy>("/policies", { method: "POST", body: JSON.stringify(body) }),
  validatePolicy: (body: unknown) =>
    request<{ valid: boolean; error?: string }>("/policies/validate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deletePolicy: (name: string) => request<void>(`/policies/${name}`, { method: "DELETE" }),
  transition: (name: string, action: string, note: string) =>
    request<Policy>(`/policies/${name}/${action}`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),

  runScan: (body: unknown) =>
    request<ScanResult>("/scans", { method: "POST", body: JSON.stringify(body) }),
  listScans: () => request<Record<string, unknown>[]>("/scans"),
  scanFindings: (scanId: string) => request<Finding[]>(`/scans/${scanId}/findings`),

  listRemediations: () => request<Remediation[]>("/remediations"),
  remediationAction: (id: string, action: string, note: string, assignee?: string) =>
    request<Remediation>(`/remediations/${id}/action`, {
      method: "POST",
      body: JSON.stringify({ action, note, assignee }),
    }),
};
