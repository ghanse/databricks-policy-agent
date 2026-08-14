"""Command-line interface: ``policy-agent validate`` and ``policy-agent scan``.

``validate`` parses and validates policy YAML files offline. ``scan`` runs a compliance
scan against a workspace, either using policies from a file/directory or the approved
policies already in storage, and (unless ``--dry-run``) persists the outcome.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from policy_agent.config import config_from_env, create_executor
from policy_agent.errors import PolicyAgentError
from policy_agent.jobs.runner import run_policy_scan
from policy_agent.policy.model import Policy, PolicyStatus, ResourceType
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
        print(f"  [{finding.severity.value}] {finding.policy_name} -> {finding.resource_name}")


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
