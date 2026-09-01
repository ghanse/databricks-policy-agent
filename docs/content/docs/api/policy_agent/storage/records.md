---
sidebar_label: records
title: policy_agent.storage.records
---

Conversions between domain objects and storage rows.

Rows are plain ``dict`` mappings keyed by column name. Readers coerce values defensively
because the Delta backend returns every column as a string while the Lakebase backend
returns native Python types; both must round-trip through the same reader.

#### policy\_to\_row

```python
def policy_to_row(policy: Policy, config: StorageConfig,
                  updated_at: datetime) -> dict[str, Any]
```

Serialises a policy to a ``policies`` row.

**Arguments**:

- `policy` - The policy to serialise.
- `config` - Storage config supplying object tags.
- `updated_at` - Timestamp recorded on the row.
  

**Returns**:

  A row mapping ready for insertion.

#### row\_to\_policy

```python
def row_to_policy(row: dict[str, Any]) -> Policy
```

Deserialises a ``policies`` row into a policy.

**Arguments**:

- `row` - The row mapping read from storage.
  

**Returns**:

  The reconstructed policy.

#### policy\_version\_to\_row

```python
def policy_version_to_row(policy: Policy, actor: str,
                          created_at: datetime) -> dict[str, Any]
```

Serialises a snapshot of a policy to a ``policy_versions`` row.

**Arguments**:

- `policy` - The policy being versioned.
- `actor` - The principal who created this version.
- `created_at` - Timestamp recorded on the row.
  

**Returns**:

  A row mapping ready for insertion.

#### scan\_to\_row

```python
def scan_to_row(scan_result: ScanResult, config: StorageConfig,
                triggered_by: str) -> dict[str, Any]
```

Serialises a scan result's header to a ``scans`` row.

**Arguments**:

- `scan_result` - The completed scan result.
- `config` - Storage config supplying object tags.
- `triggered_by` - Principal or process that initiated the scan.
  

**Returns**:

  A row mapping ready for insertion.

#### finding\_to\_row

```python
def finding_to_row(finding: Finding, scan_id: str, config: StorageConfig,
                   created_at: datetime) -> dict[str, Any]
```

Serialises a finding to a ``findings`` row.

**Arguments**:

- `finding` - The finding to serialise.
- `scan_id` - Identifier of the scan that produced the finding.
- `config` - Storage config supplying object tags.
- `created_at` - Timestamp recorded on the row.
  

**Returns**:

  A row mapping ready for insertion.

#### row\_to\_finding

```python
def row_to_finding(row: dict[str, Any]) -> Finding
```

Deserialises a ``findings`` row into a finding.

**Arguments**:

- `row` - The row mapping read from storage.
  

**Returns**:

  The reconstructed finding.

#### approval\_event\_to\_row

```python
def approval_event_to_row(event: ApprovalEvent) -> dict[str, Any]
```

Serialises an approval event to an ``approval_events`` row.

**Arguments**:

- `event` - The approval event to serialise.
  

**Returns**:

  A row mapping ready for insertion.

#### remediation\_to\_row

```python
def remediation_to_row(item: RemediationItem,
                       config: StorageConfig) -> dict[str, Any]
```

Serialises a remediation item to a ``remediations`` row.

**Arguments**:

- `item` - The remediation item to serialise.
- `config` - Storage config supplying object tags.
  

**Returns**:

  A row mapping ready for insertion.

#### row\_to\_remediation

```python
def row_to_remediation(row: dict[str, Any]) -> RemediationItem
```

Deserialises a ``remediations`` row into a remediation item.

**Arguments**:

- `row` - The row mapping read from storage.
  

**Returns**:

  The reconstructed remediation item.

#### schedule\_to\_row

```python
def schedule_to_row(schedule: ScanSchedule, config: StorageConfig,
                    updated_at: datetime) -> dict[str, Any]
```

Serialises a scan schedule to a ``schedules`` row.

**Arguments**:

- `schedule` - The schedule to serialise.
- `config` - Storage config supplying object tags.
- `updated_at` - Timestamp recorded on the row.
  

**Returns**:

  A row mapping ready for insertion.

#### row\_to\_schedule

```python
def row_to_schedule(row: dict[str, Any]) -> ScanSchedule
```

Deserialises a ``schedules`` row into a scan schedule.

**Arguments**:

- `row` - The row mapping read from storage.
  

**Returns**:

  The reconstructed schedule.

#### role\_mapping\_to\_row

```python
def role_mapping_to_row(group_name: str, role: Role, config: StorageConfig,
                        updated_at: datetime) -> dict[str, Any]
```

Serialises a group-to-role grant to a ``role_mappings`` row.

**Arguments**:

- `group_name` - The workspace group being granted a role.
- `role` - The granted role.
- `config` - Storage config supplying object tags.
- `updated_at` - Timestamp recorded on the row.
  

**Returns**:

  A row mapping ready for insertion.

#### app\_setting\_to\_row

```python
def app_setting_to_row(key: str, value: str, config: StorageConfig,
                       updated_at: datetime) -> dict[str, Any]
```

Serialise an app-settings key/value override to an ``app_settings`` row.

**Arguments**:

- `key` - The setting key.
- `value` - The setting value (already serialised to text).
- `config` - Storage config supplying object tags.
- `updated_at` - Timestamp recorded on the row.
  

**Returns**:

  A row mapping ready for insertion.

