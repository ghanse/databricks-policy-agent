"""Deployment-time policy enforcement for Databricks Asset Bundles.

The gate evaluates the same policies as a scan against resources *declared* in a bundle
(resolved via ``databricks bundle validate --output json``) before they are deployed. It is
the preventive counterpart to the detective scan.
"""

from policy_agent.enforce.bundle import load_bundle_config, resolve_bundle
from policy_agent.enforce.fix import suggest_fixes
from policy_agent.enforce.gate import run_gate
from policy_agent.enforce.model import FixSuggestion, GateResult, GateVerdict
from policy_agent.enforce.sources import snapshot_bundle

__all__ = [
    "FixSuggestion",
    "GateResult",
    "GateVerdict",
    "load_bundle_config",
    "resolve_bundle",
    "run_gate",
    "snapshot_bundle",
    "suggest_fixes",
]
