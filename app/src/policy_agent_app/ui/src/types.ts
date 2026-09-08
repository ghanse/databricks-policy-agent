export interface Condition {
  all?: Condition[];
  any?: Condition[];
  not?: Condition;
  attribute?: string;
  operator?: string;
  value?: unknown;
}

export interface Policy {
  policy: string;
  resource_type: string;
  effect: string;
  enforcement_level: string;
  status: string;
  version: number;
  description?: string;
  remediation?: string;
  rule: Condition;
  match?: Condition;
}

export interface ScanSummary {
  evaluated: number;
  compliant: number;
  violations: number;
  compliance_rate: number;
  violations_by_enforcement_level: Record<string, number>;
  violations_by_resource_type: Record<string, number>;
}

export interface Finding {
  policy_name: string;
  resource_type: string;
  resource_id: string;
  resource_name: string;
  compliant: boolean;
  enforcement_level: string;
  message: string;
  remediation: string;
  owner: string | null;
}

export interface ScanResult {
  scan_id: string;
  started_at: string;
  finished_at: string;
  summary: ScanSummary;
  violations: Finding[];
}

export interface Remediation {
  remediation_id: string;
  policy_name: string;
  resource_type: string;
  resource_id: string;
  resource_name: string;
  enforcement_level: string;
  status: string;
  assignee: string | null;
  note: string;
  scan_id: string;
  opened_at: string;
  updated_at: string;
}

export interface RemediationEvent {
  event_id: string;
  remediation_id: string;
  event_type: string;
  actor: string;
  note: string;
  from_status: string | null;
  to_status: string | null;
  payload: string;
  created_at: string | null;
}

export interface RemediationDetail extends Remediation {
  recommended_action: string;
  finding: Finding | null;
  events: RemediationEvent[];
}

export interface AgentProposal {
  proposal_id: string;
  summary: string;
  diff: string;
  changes: Record<string, unknown>;
  endpoint: string;
  /** Whether all proposed changes can be applied from this app via OBO auth. */
  applicable: boolean;
  /** Human-readable explanation when applicable is false. */
  not_applicable_reason: string;
}

export interface AgentDecision extends Remediation {
  applied: boolean;
  message: string;
}

export interface AccountUser {
  user_name: string;
  display_name: string;
  active: boolean;
}

export interface Settings {
  storage: {
    backend: string;
    catalog: string | null;
    schema: string;
    qualified_schema: string;
    object_tags: Record<string, string>;
  };
  resource_types: string[];
  operators: string[];
  roles: string[];
  notifications: { emails: string[]; webhook_configured: boolean; webhook?: string };
  workspace_url?: string;
  workspace_id?: string;
}

export interface ScanHeader {
  scan_id: string;
  started_at: string;
  finished_at: string;
  triggered_by: string;
  evaluated: string | number;
  compliant: string | number;
  violations: string | number;
}

export interface MyRoles {
  user: string;
  display_name?: string;
  roles: string[];
}
