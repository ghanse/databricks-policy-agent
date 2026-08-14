import json
import urllib.request
from contextlib import contextmanager
from datetime import UTC, datetime

from policy_agent.notify import build_scan_summary_message, notify_scan_result
from policy_agent.policy.model import Effect, ResourceType, Severity
from policy_agent.scan.results import Finding, ScanResult


def _result(*, compliant):
    finding = Finding(
        policy_name="sp-owned",
        resource_type=ResourceType.CLUSTER,
        resource_id="c1",
        resource_name="c1",
        compliant=compliant,
        effect=Effect.DENY,
        severity=Severity.HIGH,
        message="msg",
        remediation="fix",
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return ScanResult("scan-1", now, now, (finding,), ("sp-owned",), (ResourceType.CLUSTER,))


def test_build_summary_message_counts_violations():
    message = build_scan_summary_message(_result(compliant=False))
    assert message["scan_id"] == "scan-1"
    assert message["violations"] == 1
    assert message["violations_by_severity"] == {"high": 1}


def test_notify_skipped_without_webhook():
    assert notify_scan_result(_result(compliant=False), None) is False


def test_notify_skipped_when_no_violations():
    assert notify_scan_result(_result(compliant=True), "https://hook.example.com") is False


def test_notify_posts_payload_to_webhook(monkeypatch):
    captured = {}

    @contextmanager
    def _fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        yield object()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    sent = notify_scan_result(
        _result(compliant=False), "https://hook.example.com", emails=["oncall@x.com"]
    )

    assert sent is True
    assert captured["url"] == "https://hook.example.com"
    assert captured["body"]["scan_id"] == "scan-1"
    assert captured["body"]["recipients"] == ["oncall@x.com"]
