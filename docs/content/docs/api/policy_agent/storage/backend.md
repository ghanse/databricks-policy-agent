---
sidebar_label: backend
title: policy_agent.storage.backend
---

High-level persistence functions over a backend-agnostic SQL executor.

These functions are the storage API the rest of the framework calls. Each takes a
`SqlExecutor` and a `StorageConfig`, builds SQL with `schema`, and maps
rows with `records`. Mutable entities are upserted with delete-then-insert so no
vendor-specific ``MERGE``/``ON CONFLICT`` is required.

## SqlExecutor Objects

```python
class SqlExecutor(Protocol)
```

The minimal SQL surface both storage backends implement.

#### execute

```python
def execute(statement: str,
            parameters: Mapping[str, Any] | None = None) -> None
```

Executes a statement that returns no rows.

**Arguments**:

- `statement` - SQL text with ``:name`` parameter markers.
- `parameters` - Named parameter values, if any.

#### query

```python
def query(statement: str,
          parameters: Mapping[str, Any] | None = None) -> list[dict[str, Any]]
```

Executes a query and returns its rows as column-keyed mappings.

**Arguments**:

- `statement` - SQL text with ``:name`` parameter markers.
- `parameters` - Named parameter values, if any.
  

**Returns**:

  The result rows.

#### ensure\_storage

```python
def ensure_storage(executor: SqlExecutor, config: StorageConfig) -> None
```

Creates the namespace and every table if they do not already exist.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.

#### save\_policy

```python
def save_policy(executor: SqlExecutor,
                config: StorageConfig,
                policy: Policy,
                actor: str = "system") -> None
```

Upserts a policy and appends a version snapshot.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `policy` - The policy to persist.
- `actor` - The principal recorded as author of this version.

#### load\_policies

```python
def load_policies(executor: SqlExecutor,
                  config: StorageConfig,
                  status: PolicyStatus | None = None) -> list[Policy]
```

Loads policies, optionally filtered by approval status.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `status` - When provided, only policies in this status are returned.
  

**Returns**:

  The matching policies.

#### delete\_policy

```python
def delete_policy(executor: SqlExecutor, config: StorageConfig,
                  name: str) -> None
```

Deletes a policy by name.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `name` - The policy name to delete.

#### write\_scan

```python
def write_scan(executor: SqlExecutor,
               config: StorageConfig,
               scan_result: ScanResult,
               triggered_by: str = "system") -> None
```

Persists a scan's header row and one row per finding.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `scan_result` - The completed scan result.
- `triggered_by` - Principal or process that initiated the scan.

#### read\_findings

```python
def read_findings(executor: SqlExecutor,
                  config: StorageConfig,
                  scan_id: str | None = None) -> list[Finding]
```

Reads findings, optionally restricted to a single scan.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `scan_id` - When provided, only findings from this scan are returned.
  

**Returns**:

  The matching findings.

#### read\_scans

```python
def read_scans(executor: SqlExecutor,
               config: StorageConfig) -> list[dict[str, Any]]
```

Reads scan header rows, most recent first.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
  

**Returns**:

  The scan header rows as column-keyed mappings.

#### save\_approval\_event

```python
def save_approval_event(executor: SqlExecutor, config: StorageConfig,
                        event: ApprovalEvent) -> None
```

Appends an approval-workflow audit event.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `event` - The approval event to persist.

#### read\_approval\_events

```python
def read_approval_events(
        executor: SqlExecutor,
        config: StorageConfig,
        policy_name: str | None = None) -> list[dict[str, Any]]
```

Reads approval events, optionally for a single policy, most recent first.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `policy_name` - When provided, only events for this policy are returned.
  

**Returns**:

  The approval-event rows as column-keyed mappings.

#### save\_remediation

```python
def save_remediation(executor: SqlExecutor, config: StorageConfig,
                     item: RemediationItem) -> None
```

Upserts a remediation item.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `item` - The remediation item to persist.

#### read\_remediations

```python
def read_remediations(executor: SqlExecutor,
                      config: StorageConfig) -> list[RemediationItem]
```

Reads every remediation item.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
  

**Returns**:

  The remediation items.

#### save\_schedule

```python
def save_schedule(executor: SqlExecutor, config: StorageConfig,
                  schedule: ScanSchedule) -> None
```

Upserts a scan schedule.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `schedule` - The schedule to persist.

#### read\_schedules

```python
def read_schedules(executor: SqlExecutor,
                   config: StorageConfig) -> list[ScanSchedule]
```

Reads every scan schedule.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
  

**Returns**:

  The scan schedules.

#### delete\_schedule

```python
def delete_schedule(executor: SqlExecutor, config: StorageConfig,
                    schedule_id: str) -> None
```

Deletes a scan schedule by id.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `schedule_id` - The schedule to delete.

#### save\_role\_mapping

```python
def save_role_mapping(executor: SqlExecutor, config: StorageConfig,
                      group_name: str, role: Role) -> None
```

Grants a role to a workspace group (idempotent).

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `group_name` - The workspace group to grant the role to.
- `role` - The role being granted.

#### delete\_role\_mapping

```python
def delete_role_mapping(executor: SqlExecutor, config: StorageConfig,
                        group_name: str, role: Role) -> None
```

Revokes a role from a workspace group.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `group_name` - The workspace group to revoke the role from.
- `role` - The role being revoked.

#### read\_role\_mappings

```python
def read_role_mappings(executor: SqlExecutor,
                       config: StorageConfig) -> dict[str, set[Role]]
```

Reads all group-to-role grants.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
  

**Returns**:

  A mapping from group name to the set of roles granted to it.

#### read\_app\_settings

```python
def read_app_settings(executor: SqlExecutor,
                      config: StorageConfig) -> dict[str, str]
```

Read the app-settings overrides as a flat key/value mapping.

These are runtime configuration overrides an administrator sets through the app (for
example object tags or notification destinations), layered over the deploy-time defaults.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
  

**Returns**:

  A mapping from setting key to its stored (text) value.

#### save\_app\_setting

```python
def save_app_setting(executor: SqlExecutor, config: StorageConfig, key: str,
                     value: str) -> None
```

Upsert a single app-settings override.

**Arguments**:

- `executor` - The SQL executor.
- `config` - The storage configuration.
- `key` - The setting key.
- `value` - The setting value, serialised to text.

