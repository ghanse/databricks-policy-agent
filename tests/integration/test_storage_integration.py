"""Integration tests for the Unity Catalog Delta storage backend.

Requires a SQL warehouse; set ``POLICY_AGENT_WAREHOUSE_ID`` to run. The ``make_schema``
fixture provisions a scratch UC schema that is torn down automatically.
"""

import os

import pytest

from policy_agent.policy import deny, leaf
from policy_agent.policy.model import PolicyStatus
from policy_agent.scan.engine import run_scan
from policy_agent.storage import (
    DeltaSqlExecutor,
    StorageConfig,
    ensure_storage,
    load_policies,
    read_findings,
    save_policy,
    write_scan,
)


@pytest.fixture
def warehouse_id():
    value = os.environ.get("POLICY_AGENT_WAREHOUSE_ID")
    if not value:
        pytest.skip("Set POLICY_AGENT_WAREHOUSE_ID to run Delta storage integration tests.")
    return value


@pytest.mark.integration
def test_delta_storage_policy_round_trip(ws, make_schema, warehouse_id):
    schema = make_schema()
    config = StorageConfig(
        backend="uc",
        catalog=schema.catalog_name,
        schema=schema.name,
        object_tags={"managed_by": "policy-agent"},
    )
    executor = DeltaSqlExecutor(ws, warehouse_id)
    ensure_storage(executor, config)

    policy = deny(
        "sp-owned",
        "cluster",
        leaf("owner_type", "not_equals", "service_principal"),
        status="approved",
    )
    save_policy(executor, config, policy, actor="tester@example.com")

    loaded = load_policies(executor, config, status=PolicyStatus.APPROVED)
    assert any(candidate.name == "sp-owned" for candidate in loaded)


@pytest.mark.integration
def test_delta_scan_results_are_persisted(ws, make_schema, warehouse_id):
    schema = make_schema()
    config = StorageConfig(backend="uc", catalog=schema.catalog_name, schema=schema.name)
    executor = DeltaSqlExecutor(ws, warehouse_id)
    ensure_storage(executor, config)

    policy = deny("job-exists", "job", leaf("name", "exists"), status="approved")
    result = run_scan(ws, [policy])
    write_scan(executor, config, result, triggered_by="integration-test")

    persisted = read_findings(executor, config, scan_id=result.scan_id)
    assert len(persisted) == len(result.findings)
