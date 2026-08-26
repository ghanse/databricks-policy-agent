"""Scan-outcome notifications via an optional webhook.

Email notification for job *failures* is configured on the Databricks job itself; this
module handles *violation* notifications, posting a compact JSON summary to a webhook (for
example a Slack or Teams incoming webhook) using only the standard library.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Iterable

from policy_agent.scan.results import ScanResult


def build_scan_summary_message(scan_result: ScanResult) -> dict[str, object]:
    """Builds a compact, JSON-serialisable summary message for a scan result.

    Args:
        scan_result: The completed scan result.

    Returns:
        A mapping describing the scan's identity and violation counts.
    """
    summary = scan_result.summary()
    return {
        "scan_id": scan_result.scan_id,
        "finished_at": scan_result.finished_at.isoformat(),
        "evaluated": summary.evaluated,
        "violations": summary.violations,
        "compliance_rate": round(summary.compliance_rate, 4),
        "violations_by_enforcement_level": dict(summary.violations_by_enforcement_level),
        "policies": list(scan_result.policy_names),
    }


def notify_scan_result(
    scan_result: ScanResult,
    webhook_url: str | None,
    emails: Iterable[str] = (),
    timeout_seconds: float = 10.0,
) -> bool:
    """Posts a scan summary to the webhook when there are violations to report.

    Args:
        scan_result: The completed scan result.
        webhook_url: Destination webhook; when ``None`` no notification is sent.
        emails: Recipients recorded in the payload for downstream routing.
        timeout_seconds: HTTP request timeout.

    Returns:
        ``True`` if a notification was posted, ``False`` if it was skipped (no webhook or no
        violations).
    """
    if not webhook_url or scan_result.summary().violations == 0:
        return False
    payload = {"recipients": list(emails), **build_scan_summary_message(scan_result)}
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds):
        return True
