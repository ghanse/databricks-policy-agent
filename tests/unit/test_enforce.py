import json

import pytest

from policy_agent.enforce import load_bundle_config, run_gate, snapshot_bundle
from policy_agent.enforce.bundle import resolve_bundle
from policy_agent.enforce.model import GateVerdict
from policy_agent.errors import EnforcementError
from policy_agent.policy import allow, leaf
from policy_agent.policy.model import EnforcementLevel, ResourceType

BUNDLE = {
    "resources": {
        "jobs": {
            "etl": {
                "name": "prod_etl",
                "tags": {"team": "data"},
                "email_notifications": {"on_failure": ["oncall@example.com"]},
                "run_as": {"service_principal_name": "11111111-1111-1111-1111-111111111111"},
            },
            "adhoc": {"name": "adhoc"},
        }
    }
}


def _snapshots():
    return snapshot_bundle(BUNDLE)


def test_snapshot_bundle_maps_declared_jobs():
    by_id = {snapshot.resource_id: snapshot for snapshot in _snapshots()}
    assert set(by_id) == {"etl", "adhoc"}
    etl = by_id["etl"].attributes
    assert by_id["etl"].resource_type is ResourceType.JOB
    assert etl["tags"] == {"team": "data"}
    assert etl["has_email_notifications"] is True
    assert etl["owner_type"] == "service_principal"
    adhoc = by_id["adhoc"].attributes
    assert adhoc["tags"] == {}
    assert adhoc["has_email_notifications"] is False
    assert adhoc["owner_type"] == "unknown"


def test_snapshot_bundle_maps_declared_sql_warehouses():
    # A warehouse policy must see declared warehouses; otherwise a non-compliant bundle would
    # pass because the gate evaluated zero resources.
    config = {
        "resources": {
            "sql_warehouses": {
                "reporting": {
                    "name": "reporting_wh",
                    "cluster_size": "2X-Large",
                    "auto_stop_mins": 10,
                    "enable_serverless_compute": True,
                    "tags": {"custom_tags": [{"key": "team", "value": "data"}]},
                }
            }
        }
    }
    (snapshot,) = snapshot_bundle(config)
    assert snapshot.resource_type is ResourceType.SQL_WAREHOUSE
    attrs = snapshot.attributes
    assert attrs["cluster_size"] == "2X-Large"
    assert attrs["auto_stop_minutes"] == 10
    assert attrs["enable_serverless_compute"] is True
    # Warehouse tags use the {custom_tags: [{key, value}]} shape, unlike the flat job dict.
    assert attrs["tags"] == {"team": "data"}

    oversized = allow("wh-size", "sql_warehouse", leaf("cluster_size", "equals", "Medium"))
    result = run_gate([oversized], snapshot_bundle(config), fail_on=EnforcementLevel.ADVISORY)
    assert result.blocked


def test_soft_violation_warns_below_threshold_but_blocks_at_threshold():
    tagged = allow(
        "jobs-tagged", ResourceType.JOB, leaf("tags", "has_tag", "team"), enforcement_level="soft"
    )

    lenient = run_gate([tagged], _snapshots(), fail_on=EnforcementLevel.HARD)
    assert lenient.verdict is GateVerdict.PASS_WITH_WARNINGS
    assert not lenient.blocked
    assert {f.resource_id for f in lenient.warnings} == {"adhoc"}

    strict = run_gate([tagged], _snapshots(), fail_on=EnforcementLevel.SOFT)
    assert strict.blocked
    assert {f.resource_id for f in strict.blocking} == {"adhoc"}


def test_soft_violation_can_be_overridden():
    tagged = allow(
        "jobs-tagged", ResourceType.JOB, leaf("tags", "has_tag", "team"), enforcement_level="soft"
    )
    result = run_gate(
        [tagged],
        _snapshots(),
        fail_on=EnforcementLevel.SOFT,
        overrides=frozenset({"jobs-tagged"}),
        override_reason="tracked in JIRA-123",
    )
    assert not result.blocked
    assert result.verdict is GateVerdict.PASS_WITH_WARNINGS
    assert {f.resource_id for f in result.overridden} == {"adhoc"}


def test_hard_violation_blocks_and_cannot_be_overridden():
    must_notify = allow(
        "jobs-notify",
        ResourceType.JOB,
        leaf("has_email_notifications", "equals", True),
        enforcement_level="hard",
    )
    result = run_gate(
        [must_notify],
        _snapshots(),
        fail_on=EnforcementLevel.HARD,
        overrides=frozenset({"jobs-notify"}),
        override_reason="attempted override",
    )
    assert result.blocked
    assert {f.resource_id for f in result.blocking} == {"adhoc"}
    assert result.overridden == ()


def test_clean_bundle_passes_with_fixes_suggested():
    tagged = allow(
        "jobs-tagged", ResourceType.JOB, leaf("tags", "has_tag", "team"), enforcement_level="hard"
    )
    result = run_gate(
        [tagged], _snapshots(), fail_on=EnforcementLevel.HARD, suggest_remediations=True
    )
    assert result.blocked
    assert [fix.resource_id for fix in result.fixes] == ["adhoc"]
    assert result.to_dict()["verdict"] == "blocked"


def test_load_bundle_config_from_json_file(tmp_path):
    path = tmp_path / "resolved.json"
    path.write_text(json.dumps(BUNDLE), encoding="utf-8")
    assert load_bundle_config(path)["resources"]["jobs"]["etl"]["name"] == "prod_etl"


def test_resolve_bundle_reports_missing_directory(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(EnforcementError, match="Bundle directory does not exist"):
        resolve_bundle(missing)


def test_resolve_bundle_reports_missing_file(tmp_path):
    missing = tmp_path / "not_exists.json"
    with pytest.raises(EnforcementError, match=f"Bundle JSON file does not exist: {missing}"):
        load_bundle_config(missing)
