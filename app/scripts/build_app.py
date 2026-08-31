"""Assemble the deployable Databricks App source tree under ``app/.build``.

Steps:
    1. Build the React SPA (``npm install`` + ``npm run build``) into ``ui/dist``.
    2. Build the library wheel with ``uv build`` from the repository root.
    3. Copy the backend package (including the built ``ui/dist``) and the wheel into
       ``.build/``, and write ``requirements.txt`` and ``app.yaml`` so the Databricks App
       runtime can install dependencies and launch uvicorn.

Run from the ``app`` directory: ``uv run python scripts/build_app.py``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_DIR.parent
UI_DIR = APP_DIR / "src" / "policy_agent_app" / "ui"
BUILD_DIR = APP_DIR / ".build"


def main() -> None:
    """Build the SPA and library wheel, then assemble the deployable source tree."""
    _run(["npm", "install"], cwd=UI_DIR)
    _run(["npm", "run", "build"], cwd=UI_DIR)
    _run(["uv", "build", "--wheel", "--out-dir", str(APP_DIR / ".wheels")], cwd=REPO_ROOT)

    _reset_build_dir()
    # Copy the backend package and the built ``ui/dist``; drop build inputs (node_modules,
    # TypeScript sources) and bytecode caches that the runtime does not need.
    shutil.copytree(
        APP_DIR / "src" / "policy_agent_app",
        BUILD_DIR / "policy_agent_app",
        ignore=shutil.ignore_patterns("__pycache__", "node_modules", "src", "*.ts", "*.tsx"),
    )
    wheel = _copy_wheel()
    _write_requirements(wheel.name)
    _write_app_yaml()
    print(f"Assembled deployable app at {BUILD_DIR}")


def _reset_build_dir() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)


def _copy_wheel() -> Path:
    wheels = sorted((APP_DIR / ".wheels").glob("*.whl"))
    if not wheels:
        raise SystemExit("No library wheel was produced by 'uv build'.")
    destination = BUILD_DIR / wheels[-1].name
    shutil.copy2(wheels[-1], destination)
    return destination


def _write_requirements(wheel_name: str) -> None:
    requirements = [
        wheel_name,
        "psycopg[binary]>=3.1,<4.0",
        "SQLAlchemy>=2.0,<3.0",
        "fastapi>=0.115.0,<1.0",
        "uvicorn[standard]>=0.30.0,<1.0",
        "pydantic>=2.7.0,<3.0",
    ]
    (BUILD_DIR / "requirements.txt").write_text("\n".join(requirements) + "\n", encoding="utf-8")


def _write_app_yaml() -> None:
    command = (
        "command:\n"
        '  ["uvicorn", "policy_agent_app.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]\n'
    )
    (BUILD_DIR / "app.yaml").write_text(command + _env_block(), encoding="utf-8")


def _env_block() -> str:
    """Build the app.yaml ``env`` block from POLICY_AGENT_* config in the build environment.

    Databricks Apps read runtime environment from ``app.yaml``, so the configuration present
    when the app tree is assembled is baked in here. The SQL warehouse id is resolved at
    runtime from the app resource named ``policy-agent-warehouse`` rather than as a literal.

    Returns:
        The YAML ``env:`` block, or an empty string when no configuration is set.
    """
    passthrough = (
        "POLICY_AGENT_STORAGE_BACKEND",
        "POLICY_AGENT_CATALOG",
        "POLICY_AGENT_SCHEMA",
        "POLICY_AGENT_TAGS",
        "POLICY_AGENT_NOTIFICATION_EMAILS",
        "POLICY_AGENT_NOTIFICATION_WEBHOOK",
        "POLICY_AGENT_LAKEBASE_URL",
    )
    lines = ["env:"]
    for name in passthrough:
        value = os.environ.get(name)
        if value:
            lines.append(f"  - name: {name}")
            lines.append(f'    value: "{value}"')
    lines.append("  - name: POLICY_AGENT_WAREHOUSE_ID")
    lines.append('    valueFrom: "policy-agent-warehouse"')
    return "\n".join(lines) + "\n"


def _run(command: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(command)}  (in {cwd})")
    subprocess.run(command, cwd=cwd, check=True)


if __name__ == "__main__":
    main()
