"""Test fixtures: an in-memory executor and a TestClient wired with fake state.

The client is built without running the real lifespan; process state (config, executor,
workspace client) is set directly on ``app.state`` and the role dependency is overridden so
the whole API can be exercised offline.
"""

from __future__ import annotations

import re
from collections import defaultdict
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from policy_agent.approval.roles import Role
from policy_agent.config import PolicyAgentConfig
from policy_agent.storage.config import BACKEND_LAKEBASE, StorageConfig

from policy_agent_app.backend.app import create_app
from policy_agent_app.backend.auth import current_roles


class FakeExecutor:
    def __init__(self):
        self.tables = defaultdict(list)

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
        users=SimpleNamespace(list=lambda **_kw: []),
    )


@pytest.fixture
def executor():
    return FakeExecutor()


@pytest.fixture
def fake_clusters():
    return [_fake_cluster("c1", "alice@example.com")]


@pytest.fixture
def make_client(executor, fake_clusters):
    def _build(roles=frozenset({Role.ADMIN})):
        config = PolicyAgentConfig(
            storage=StorageConfig(backend=BACKEND_LAKEBASE, schema="policy_agent")
        )
        app = create_app()
        app.state.config = config
        app.state.executor = executor
        app.state.workspace_client = _fake_workspace_client(fake_clusters)
        app.dependency_overrides[current_roles] = lambda: set(roles)
        return TestClient(app)

    return _build


@pytest.fixture
def client(make_client):
    return make_client()
