---
sidebar_label: notify
title: policy_agent.notify
---

Scan-outcome notifications via an optional webhook.

Email notification for job *failures* is configured on the Databricks job itself; this
module handles *violation* notifications, posting a compact JSON summary to a webhook (for
example a Slack or Teams incoming webhook) using only the standard library.

#### build\_scan\_summary\_message

```python
def build_scan_summary_message(scan_result: ScanResult) -> dict[str, object]
```

Builds a compact, JSON-serialisable summary message for a scan result.

**Arguments**:

- `scan_result` - The completed scan result.
  

**Returns**:

  A mapping describing the scan's identity and violation counts.

#### notify\_scan\_result

```python
def notify_scan_result(scan_result: ScanResult,
                       webhook_url: str | None,
                       emails: Iterable[str] = (),
                       timeout_seconds: float = 10.0) -> bool
```

Posts a scan summary to the webhook when there are violations to report.

**Arguments**:

- `scan_result` - The completed scan result.
- `webhook_url` - Destination webhook; when ``None`` no notification is sent.
- `emails` - Recipients recorded in the payload for downstream routing.
- `timeout_seconds` - HTTP request timeout.
  

**Returns**:

  ``True`` if a notification was posted, ``False`` if it was skipped (no webhook or no
  violations).

