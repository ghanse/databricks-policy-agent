"""Backend round-trip tests using an in-memory executor that mimics Lakebase semantics.

The fake executor interprets the small, known set of SQL shapes the schema builders emit and
stores native Python values, so ``save`` then ``load`` exercises the real schema, records,
and backend code paths end to end.
"""

import re
from collections import defaultdict
from datetime import UTC, datetime
from types import SimpleNamespace

from policy_agent.approval import Role, submit_for_review
from policy_agent.policy import allow, deny, leaf
from policy_agent.policy.model import PolicyStatus
from policy_agent.remediation import open_items_from_findings, resolve
from policy_agent.scan.engine import run_scan
from policy_agent.storage import (
    BACKEND_LAKEBASE,
    StorageConfig,
    ensure_storage,
    load_policies,
    read_approval_events,
    read_findings,
    read_remediations,
    read_scans,
    save_approval_event,
    save_policy,
    save_remediation,
    write_scan,
)


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


def _config():
    return StorageConfig(backend=BACKEND_LAKEBASE, schema="policy_agent", object_tags={"team": "x"})


def _cluster(cluster_id, creator):
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


def _ws(clusters):
    empty = SimpleNamespace(list=lambda **_kw: [])
    return SimpleNamespace(
        jobs=empty,
        clusters=SimpleNamespace(list=lambda **_kw: list(clusters)),
        warehouses=empty,
        apps=empty,
        serving_endpoints=empty,
    )


class RecordingExecutor:
    """Records executed DDL and answers the catalog-existence probe."""

    def __init__(self, catalog_present):
        self.catalog_present = catalog_present
        self.executed = []

    def execute(self, statement, parameters=None):
        self.executed.append(statement.strip())

    def query(self, statement, parameters=None):
        if statement.strip().upper().startswith("SHOW SCHEMAS IN"):
            if not self.catalog_present:
                raise RuntimeError("catalog not found")
            return [{"databaseName": "default"}]
        return []


def _uc_config():
    return StorageConfig(backend="uc", catalog="governance", schema="policy_agent")


def test_ensure_storage_skips_catalog_creation_when_catalog_exists():
    executor = RecordingExecutor(catalog_present=True)
    ensure_storage(executor, _uc_config())
    assert not any(s.startswith("CREATE CATALOG") for s in executor.executed)
    assert any(
        s.startswith("CREATE SCHEMA IF NOT EXISTS governance.policy_agent")
        for s in executor.executed
    )


def test_ensure_storage_creates_catalog_when_absent():
    executor = RecordingExecutor(catalog_present=False)
    ensure_storage(executor, _uc_config())
    assert any(s.startswith("CREATE CATALOG IF NOT EXISTS governance") for s in executor.executed)


def test_save_and_load_policy_round_trip():
    executor, config = FakeExecutor(), _config()
    ensure_storage(executor, config)
    original = deny(
        "sp-owned",
        "cluster",
        leaf("owner_type", "not_equals", "service_principal"),
        description="Compute owned by SP",
        remediation="Reassign owner.",
        status="approved",
    )

    save_policy(executor, config, original, actor="alice@example.com")
    loaded = load_policies(executor, config)

    assert loaded == [original]
    assert len(executor.tables["policy_agent.policy_versions"]) == 1


def test_save_policy_is_an_upsert():
    executor, config = FakeExecutor(), _config()
    policy = allow("named", "job", leaf("name", "matches_regex", "^prod_.+$"))
    save_policy(executor, config, policy)
    save_policy(executor, config, policy)
    assert len(executor.tables["policy_agent.policies"]) == 1


def test_load_policies_filters_by_status():
    executor, config = FakeExecutor(), _config()
    save_policy(executor, config, deny("a", "job", leaf("name", "exists"), status="approved"))
    save_policy(executor, config, deny("b", "job", leaf("name", "exists"), status="draft"))
    approved = load_policies(executor, config, status=PolicyStatus.APPROVED)
    assert [p.name for p in approved] == ["a"]


def test_write_scan_persists_header_and_findings():
    executor, config = FakeExecutor(), _config()
    policy = deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    result = run_scan(_ws([_cluster("c1", "alice@example.com")]), [policy])

    write_scan(executor, config, result, triggered_by="scheduled")

    scans = read_scans(executor, config)
    assert len(scans) == 1
    assert scans[0]["violations"] == 1
    assert scans[0]["triggered_by"] == "scheduled"

    findings = read_findings(executor, config, scan_id=result.scan_id)
    assert len(findings) == 1
    assert findings[0].compliant is False
    assert findings[0].resource_id == "c1"


def test_object_tags_are_stamped_on_rows():
    executor, config = FakeExecutor(), _config()
    save_policy(executor, config, deny("a", "job", leaf("name", "exists")))
    row = executor.tables["policy_agent.policies"][0]
    assert row["object_tags"] == '{"team": "x"}'


def test_timestamps_are_written_as_datetimes():
    executor, config = FakeExecutor(), _config()
    save_policy(executor, config, deny("a", "job", leaf("name", "exists")))
    assert isinstance(executor.tables["policy_agent.policies"][0]["updated_at"], datetime)
    assert executor.tables["policy_agent.policies"][0]["updated_at"].tzinfo == UTC


def test_approval_event_round_trip():
    executor, config = FakeExecutor(), _config()
    _, event = submit_for_review(
        deny("a", "job", leaf("name", "exists")), "alice@example.com", {Role.POLICY_AUTHOR}
    )
    save_approval_event(executor, config, event)
    rows = read_approval_events(executor, config, policy_name="a")
    assert rows[0]["to_status"] == "in_review"
    assert rows[0]["actor"] == "alice@example.com"


def test_remediation_upsert_and_read_round_trip():
    executor, config = FakeExecutor(), _config()
    policy = deny("sp-owned", "cluster", leaf("owner_type", "not_equals", "service_principal"))
    result = run_scan(_ws([_cluster("c1", "alice@example.com")]), [policy])
    (item,) = open_items_from_findings(result.violations, result.scan_id, result.finished_at)

    save_remediation(executor, config, item)
    save_remediation(executor, config, resolve(item, result.finished_at, note="fixed"))

    stored = read_remediations(executor, config)
    assert len(stored) == 1
    assert stored[0].status.value == "resolved"
    assert stored[0].note == "fixed"


def test_app_settings_round_trip():
    from policy_agent.storage.backend import read_app_settings, save_app_setting

    executor, config = FakeExecutor(), _config()
    ensure_storage(executor, config)
    assert read_app_settings(executor, config) == {}

    save_app_setting(executor, config, "object_tags", '{"team": "x"}')
    save_app_setting(executor, config, "notification_webhook", "https://hooks.example/x")
    assert read_app_settings(executor, config) == {
        "object_tags": '{"team": "x"}',
        "notification_webhook": "https://hooks.example/x",
    }

    # Upsert replaces the prior value rather than appending a second row.
    save_app_setting(executor, config, "object_tags", '{"team": "y"}')
    assert read_app_settings(executor, config)["object_tags"] == '{"team": "y"}'
