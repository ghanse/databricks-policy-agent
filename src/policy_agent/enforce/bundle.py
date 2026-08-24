"""Resolve a Databricks Asset Bundle to its fully-substituted configuration.

``databricks bundle validate --output json`` emits the resolved bundle (all variables and
target overrides applied). That JSON is the desired-state manifest the enforcement gate
evaluates before ``databricks bundle deploy`` runs — the DAB analogue of a Terraform plan.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from policy_agent.errors import EnforcementError


def load_bundle_config(source: str | Path, target: str | None = None) -> dict[str, Any]:
    """Load a resolved bundle configuration from a JSON file or by resolving a bundle dir.

    Args:
        source: Either a path to a ``bundle validate --output json`` file, or a bundle
            directory to resolve.
        target: Bundle target to resolve when ``source`` is a directory.

    Returns:
        The resolved bundle configuration.

    Raises:
        EnforcementError: If the file cannot be parsed or the bundle cannot be resolved.
    """
    path = Path(source)
    if path.suffix == ".json" and path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise EnforcementError(f"Could not parse bundle JSON {path}: {error}") from error
    return resolve_bundle(path, target)


def resolve_bundle(bundle_dir: str | Path, target: str | None = None) -> dict[str, Any]:
    """Run ``databricks bundle validate --output json`` and return the parsed config.

    Args:
        bundle_dir: Directory containing ``databricks.yml``.
        target: Bundle target to resolve (``-t``); the bundle default is used when ``None``.

    Returns:
        The resolved bundle configuration.

    Raises:
        EnforcementError: If the CLI is missing, validation fails, or output is not JSON.
    """
    command = ["databricks", "bundle", "validate", "--output", "json"]
    if target:
        command += ["-t", target]
    try:
        completed = subprocess.run(
            command, cwd=str(bundle_dir), capture_output=True, text=True, check=False
        )
    except FileNotFoundError as error:
        raise EnforcementError("The 'databricks' CLI is required to resolve a bundle.") from error
    if completed.returncode != 0:
        raise EnforcementError(f"`databricks bundle validate` failed: {completed.stderr.strip()}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise EnforcementError(f"Bundle validation did not emit JSON: {error}") from error
