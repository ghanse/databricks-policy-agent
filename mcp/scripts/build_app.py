"""Assembles the deployable Databricks App source tree for the MCP server under ``mcp/.build``.

Steps:
    1. Build the library wheel with ``uv build`` from the repository root.
    2. Copy the ``policy_agent_mcp`` package and the wheel into ``.build/``, and write
       ``requirements.txt`` and ``app.yaml`` so the Databricks App runtime can install
       dependencies and launch the server.

Run from the ``mcp`` directory: ``uv run python scripts/build_app.py``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

MCP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = MCP_DIR.parent
BUILD_DIR = MCP_DIR / ".build"


def main() -> None:
    """Builds the library wheel, then assembles the deployable source tree."""
    _run(["uv", "build", "--wheel", "--out-dir", str(MCP_DIR / ".wheels")], cwd=REPO_ROOT)

    _reset_build_dir()
    # Copy the server package; drop bytecode caches the runtime does not need.
    shutil.copytree(
        MCP_DIR / "src" / "policy_agent_mcp",
        BUILD_DIR / "policy_agent_mcp",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    wheel = _copy_wheel()
    _write_requirements(wheel.name)
    _write_app_yaml()
    print(f"Assembled deployable MCP app at {BUILD_DIR}")


def _reset_build_dir() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)


def _copy_wheel() -> Path:
    wheels = sorted((MCP_DIR / ".wheels").glob("*.whl"))
    if not wheels:
        raise SystemExit("No library wheel was produced by 'uv build'.")
    destination = BUILD_DIR / wheels[-1].name
    shutil.copy2(wheels[-1], destination)
    return destination


def _write_requirements(wheel_name: str) -> None:
    requirements = [
        wheel_name,
        "mcp>=1.2.0,<2.0",
        "databricks-sdk>=0.83.0,<1.0",
        # Lakebase-backed deployments read stored policy state through Postgres.
        "psycopg[binary]>=3.1,<4.0",
        "SQLAlchemy>=2.0,<3.0",
    ]
    (BUILD_DIR / "requirements.txt").write_text("\n".join(requirements) + "\n", encoding="utf-8")


def _write_app_yaml() -> None:
    app_yaml = 'command: ["python", "-m", "policy_agent_mcp.server"]\n'
    (BUILD_DIR / "app.yaml").write_text(app_yaml, encoding="utf-8")


def _run(command: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(command)}  (in {cwd})")
    subprocess.run(command, cwd=cwd, check=True)


if __name__ == "__main__":
    main()
