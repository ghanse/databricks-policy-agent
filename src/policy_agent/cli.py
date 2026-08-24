"""Command-line interface: ``validate``, ``scan``, and ``enforce``.

``validate`` parses and validates policy YAML files offline. ``scan`` runs a compliance
scan against a workspace, either using policies from a file/directory or the approved
policies already in storage, and (unless ``--dry-run``) persists the outcome. ``enforce``
gates a Databricks Asset Bundle's *declared* resources before deployment.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from policy_agent.config import config_from_env, create_executor
from policy_agent.enforce import load_bundle_config, run_gate, snapshot_bundle
from policy_agent.enforce.model import GateResult
from policy_agent.errors import PolicyAgentError
from policy_agent.jobs.runner import run_policy_scan
from policy_agent.policy.model import EnforcementLevel, Policy, PolicyStatus, ResourceType
from policy_agent.policy.yaml_loader import load_policies_from_yaml
from policy_agent.scan.engine import run_scan
from policy_agent.scan.results import ScanResult
from policy_agent.storage.backend import load_policies


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments to parse; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        return _run_validate(args.paths)
    if args.command == "enforce":
        return _run_enforce(args)
    return _run_scan(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="policy-agent", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate policy YAML files.")
    validate.add_argument("paths", nargs="+", help="Policy YAML files or directories.")

    scan = subparsers.add_parser("scan", help="Run a compliance scan against a workspace.")
    scan.add_argument(
        "--profile", default=None, help="Databricks CLI profile to authenticate with."
    )
    scan.add_argument(
        "--policies",
        default=None,
        help="Policy YAML file or directory; defaults to approved policies in storage.",
    )
    scan.add_argument(
        "--resource-types",
        default=None,
        help="Comma-separated resource types to restrict the scan to.",
    )
    scan.add_argument("--dry-run", action="store_true", help="Evaluate without writing results.")

    enforce = subparsers.add_parser(
        "enforce", help="Gate a Databricks Asset Bundle's declared resources against policies."
    )
    enforce.add_argument(
        "--bundle", default=".", help="Bundle directory, or a resolved 'bundle validate' JSON file."
    )
    enforce.add_argument("--target", default=None, help="Bundle target to resolve.")
    enforce.add_argument(
        "--policies",
        default=None,
        help="Policy YAML file or directory; defaults to approved policies in storage.",
    )
    enforce.add_argument(
        "--fail-on",
        choices=["advisory", "soft", "hard"],
        default="hard",
        help="Minimum enforcement level that blocks the deployment (default: hard).",
    )
    enforce.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="POLICY",
        help="Policy name to override; soft violations only. Repeatable.",
    )
    enforce.add_argument(
        "--override-reason",
        default="",
        help="Reason recorded for overrides; required when --override is used.",
    )
    enforce.add_argument(
        "--fix", action="store_true", help="Include suggested remediations for violations."
    )
    enforce.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format."
    )
    return parser


def _run_validate(paths: list[str]) -> int:
    error_count = 0
    for file_path in _iter_yaml_files(paths):
        try:
            policies = load_policies_from_yaml(file_path)
            print(f"OK  {file_path}: {len(policies)} policy(ies)")
        except PolicyAgentError as error:
            error_count += 1
            print(f"ERR {file_path}: {error}")
    return 1 if error_count else 0


def _run_scan(args: argparse.Namespace) -> int:
    from databricks.sdk import WorkspaceClient

    workspace_client = WorkspaceClient(profile=args.profile) if args.profile else WorkspaceClient()
    config = config_from_env()
    resource_types = _parse_resource_types(args.resource_types)

    if args.policies:
        policies = _load_policy_files(args.policies)
        if args.dry_run:
            result = run_scan(workspace_client, policies, resource_types)
        else:
            executor = create_executor(config, workspace_client)
            result = run_policy_scan(
                workspace_client, executor, config, policies, "cli", resource_types
            )
    else:
        executor = create_executor(config, workspace_client)
        policies = load_policies(executor, config.storage, status=PolicyStatus.APPROVED)
        result = (
            run_scan(workspace_client, policies, resource_types)
            if args.dry_run
            else run_policy_scan(
                workspace_client, executor, config, policies, "cli", resource_types
            )
        )

    _print_summary(result)
    return 0


def _print_summary(result: ScanResult) -> None:
    summary = result.summary()
    print(
        f"scan {result.scan_id}: evaluated {summary.evaluated}, "
        f"violations {summary.violations}, compliance {summary.compliance_rate:.1%}"
    )
    for finding in result.violations:
        level = finding.enforcement_level.value
        print(f"  [{level}] {finding.policy_name} -> {finding.resource_name}")


def _run_enforce(args: argparse.Namespace) -> int:
    overrides = frozenset(args.override)
    if overrides and not args.override_reason:
        print("ERR --override requires --override-reason.")
        return 2
    policies = _resolve_enforce_policies(args)
    config = load_bundle_config(args.bundle, args.target)
    snapshots = snapshot_bundle(config)
    result = run_gate(
        policies,
        snapshots,
        fail_on=EnforcementLevel(args.fail_on),
        overrides=overrides,
        override_reason=args.override_reason,
        suggest_remediations=args.fix,
    )
    if args.output == "json":
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_gate(result)
    return 1 if result.blocked else 0


def _resolve_enforce_policies(args: argparse.Namespace) -> list[Policy]:
    if args.policies:
        return _load_policy_files(args.policies)
    from databricks.sdk import WorkspaceClient

    config = config_from_env()
    executor = create_executor(config, WorkspaceClient())
    return load_policies(executor, config.storage, status=PolicyStatus.APPROVED)


def _print_gate(result: GateResult) -> None:
    print(
        f"gate: {result.verdict.value} ({len(result.blocking)} blocking, "
        f"{len(result.overridden)} overridden, {len(result.warnings)} warnings)"
    )
    for finding in result.blocking:
        print(
            f"  BLOCK    [{finding.enforcement_level.value}] {finding.policy_name} "
            f"-> {finding.resource_type.value}:{finding.resource_id}"
        )
    for finding in result.overridden:
        print(
            f"  OVERRIDE [{finding.enforcement_level.value}] {finding.policy_name} "
            f"-> {finding.resource_type.value}:{finding.resource_id}"
        )
    for finding in result.warnings:
        print(
            f"  WARN     [{finding.enforcement_level.value}] {finding.policy_name} "
            f"-> {finding.resource_type.value}:{finding.resource_id}"
        )
    for fix in result.fixes:
        print(f"  FIX      {fix.policy_name} -> {fix.resource_id}: {fix.guidance}")
    if result.override_reason:
        print(f"  override reason: {result.override_reason}")


def _iter_yaml_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(p for p in path.iterdir() if p.suffix in {".yml", ".yaml"}))
        else:
            files.append(path)
    return files


def _load_policy_files(source: str) -> list[Policy]:
    policies: list[Policy] = []
    for file_path in _iter_yaml_files([source]):
        policies.extend(load_policies_from_yaml(file_path))
    return policies


def _parse_resource_types(raw: str | None) -> list[ResourceType] | None:
    if not raw:
        return None
    return [ResourceType(item.strip()) for item in raw.split(",") if item.strip()]


if __name__ == "__main__":
    sys.exit(main())
