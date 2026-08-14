"""Workspace scanning: fetch resources, evaluate policies, produce findings.

from policy_agent.scan import run_scan, ScanResult, Finding
"""

from policy_agent.scan.engine import collect_snapshots, run_scan
from policy_agent.scan.evaluator import evaluate_resource
from policy_agent.scan.registry import (
    RESOURCE_SCANNERS,
    scanner_for,
    supported_resource_types,
)
from policy_agent.scan.resources import classify_principal
from policy_agent.scan.results import (
    Finding,
    ResourceSnapshot,
    ScanResult,
    ScanSummary,
)

__all__ = [
    "RESOURCE_SCANNERS",
    "Finding",
    "ResourceSnapshot",
    "ScanResult",
    "ScanSummary",
    "classify_principal",
    "collect_snapshots",
    "evaluate_resource",
    "run_scan",
    "scanner_for",
    "supported_resource_types",
]
