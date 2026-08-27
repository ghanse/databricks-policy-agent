"""Test fixtures: an in-memory storage executor and a ServerContext wired with fakes.

The executor mimics the SQL surface both real backends implement (insert/delete/select by
table), so the storage-backed tools can be exercised entirely offline. The workspace client
is a namespace exposing just the services the scan tools touch.
"""

from __future__ import annotations

import re
from collections import defaultdict
from types import SimpleNamespace

import pytest
from policy_agent.config import PolicyAgentConfig
from policy_agent.storage.config import BACKEND_LAKEBASE, StorageConfig

from policy_agent_mcp.context import ServerContext


class FakeExecutor:
    """An in-memory `SqlExecutor` keyed by table name."""

    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = defaultdict(list)

    def execute(self, statement, parameters=None):
        stripped = statement.strip()
        upper = stripped.upper()
        if upper.startswith("INSERT INTO"):
            self.tables[_table(stripped, "INSERT INTO ")].append(dict(parameters or {}))
        elif upper.startswith("DELETE FROM"):
            table = _table(stripped, "DELETE FROM ")
            self.tables[table] = [r for r in self.tables[table] if not _matches(r, parameters)]

    def query(self, statement, parameters=None):
        rows = self.tables[_table(statement.strip(), "FROM ")]
        return [dict(r) for r in rows if _matches(r, parameters)]


def _table(sql, marker):
    tail = sql[sql.index(marker) + len(marker) :]
    return re.split(r"[\s(]", tail, maxsplit=1)[0]


def _matches(row, parameters):
    if not parameters:
        return True
    return all(row.get(key) == value for key, value in parameters.items())


def _fake_cluster(cluster_id, creator):
    return SimpleNamespace(
        cluster_id=cluster_id,
        cluster_name=cluster_id,
        creator_user_name=creator,
        custom_tags={},
        start_time=None,
        cluster_source=SimpleNamespace(value="UI"),
        autotermination_minutes=0,
        spark_version="14.3",
        node_type_id="i3.xlarge",
        num_workers=1,
        data_security_mode=None,
        single_user_name=None,
    )


def _fake_workspace_client(clusters):
    empty = SimpleNamespace(list=lambda **_kw: [])
    return SimpleNamespace(
        jobs=empty,
        clusters=SimpleNamespace(list=lambda **_kw: list(clusters)),
        warehouses=empty,
        apps=empty,
        serving_endpoints=empty,
    )


@pytest.fixture
def executor():
    return FakeExecutor()


@pytest.fixture
def fake_clusters():
    # A user-owned cluster: violates a "clusters must be owned by a service principal" policy.
    return [_fake_cluster("c1", "alice@example.com")]


@pytest.fixture
def context(executor, fake_clusters):
    config = PolicyAgentConfig(
        storage=StorageConfig(backend=BACKEND_LAKEBASE, schema="policy_agent")
    )
    return ServerContext(
        config=config,
        workspace_client=_fake_workspace_client(fake_clusters),
        executor=executor,
    )
