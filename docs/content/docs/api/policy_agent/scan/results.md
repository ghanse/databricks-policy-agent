---
sidebar_label: results
title: policy_agent.scan.results
---

Scan output types: resource snapshots, findings, and aggregated summaries.

A scan produces one `Finding` per applicable (policy, resource) pair. Findings are the
atomic unit persisted to storage and rendered in the app; `ScanSummary` derives the
headline counts a dashboard shows without re-scanning.

## ResourceSnapshot Objects

```python
@dataclass(frozen=True)
class ResourceSnapshot()
```

A normalized, evaluable view of one workspace resource.

**Attributes**:

- `resource_type` - The type of resource this snapshot describes.
- `attributes` - Flat mapping of attribute names to values that policy conditions read.
  Always contains the common attributes ``id``, ``name``, ``owner``,
  ``owner_type``, ``tags``, and ``created_time``.

#### resource\_id

```python
@property
def resource_id() -> str
```

The resource's stable identifier.

#### name

```python
@property
def name() -> str
```

The resource's display name.

#### owner

```python
@property
def owner() -> str | None
```

The resource's owner principal, if known.

## Finding Objects

```python
@dataclass(frozen=True)
class Finding()
```

The outcome of evaluating one policy against one resource.

**Attributes**:

- `policy_name` - Name of the evaluated policy.
- `resource_type` - Type of the evaluated resource.
- `resource_id` - Identifier of the evaluated resource.
- `resource_name` - Display name of the evaluated resource.
- `compliant` - ``True`` when the resource satisfies the policy.
- `effect` - The evaluated policy's effect.
- `enforcement` - The evaluated policy's enforcement level.
- `message` - Human-readable explanation of the outcome.
- `remediation` - Guidance for resolving a violation (empty when compliant).
- `owner` - The resource owner principal, if known.

## ScanSummary Objects

```python
@dataclass(frozen=True)
class ScanSummary()
```

Aggregated counts derived from a scan's findings.

**Attributes**:

- `evaluated` - Total number of (policy, resource) evaluations performed.
- `compliant` - Number of evaluations that were compliant.
- `violations` - Number of evaluations that were violations.
- `violations_by_enforcement` - Violation counts keyed by enforcement level.
- `violations_by_resource_type` - Violation counts keyed by resource-type value.

#### compliance\_rate

```python
@property
def compliance_rate() -> float
```

Fraction of evaluations that were compliant, in the range ``[0.0, 1.0]``.

## ScanResult Objects

```python
@dataclass(frozen=True)
class ScanResult()
```

The complete result of a single scan run.

**Attributes**:

- `scan_id` - Unique identifier for this scan run.
- `started_at` - When the scan began.
- `finished_at` - When the scan completed.
- `findings` - Every applicable (policy, resource) evaluation.
- `policy_names` - Names of the policies included in the scan.
- `resource_types` - Resource types included in the scan.

#### violations

```python
@property
def violations() -> tuple[Finding, ...]
```

The subset of findings that are violations.

#### summary

```python
def summary() -> ScanSummary
```

Compute the aggregated summary for this scan.

**Returns**:

  A `ScanSummary` describing evaluation and violation counts.

