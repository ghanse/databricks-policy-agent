"""Integration-test configuration.

These tests require a live Databricks workspace and are marked ``integration``. The Databricks
Labs pytester plugin — registered automatically as a pytest entry point — supplies the ``ws``,
``make_job``, ``make_cluster``, ``make_warehouse``, ``make_schema``, and ``make_random``
fixtures, and tears down everything it creates.

Authentication uses the standard Databricks SDK environment. Locally, the ambient CLI profile
works; in CI the workspace host and a service principal are provided via environment variables
(``DATABRICKS_HOST``, ``DATABRICKS_CLIENT_ID``, ``DATABRICKS_CLIENT_SECRET`` for OAuth M2M). The
Delta storage tests additionally require ``POLICY_AGENT_WAREHOUSE_ID`` and skip without it.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Generator

import pytest


@pytest.fixture
def managed_location(ws) -> str:
    override = os.environ.get("POLICY_AGENT_MANAGED_LOCATION")
    if override:
        return override.rstrip("/")
    preferred = os.environ.get("POLICY_AGENT_EXTERNAL_LOCATION")
    locations = list(ws.external_locations.list())
    if not locations:
        pytest.skip("no external location available for catalog managed storage")
    chosen = next((loc for loc in locations if loc.name == preferred), None) or locations[0]
    return str(chosen.url).rstrip("/")


@pytest.fixture
def make_catalog(
    ws, make_random, watchdog_remove_after, managed_location
) -> Generator[Callable[..., object], None, None]:
    created = []

    def create(*, name: str | None = None):
        name = name or f"dummy_c{make_random(8)}".lower()
        info = ws.catalogs.create(
            name=name,
            storage_root=f"{managed_location}/{name}",
            properties={"RemoveAfter": watchdog_remove_after},
        )
        created.append(info)
        return info

    yield create

    for info in created:
        try:
            ws.catalogs.delete(info.full_name, force=True)
        except Exception:  # noqa: BLE001 - best-effort teardown; never fail a test on cleanup
            pass
