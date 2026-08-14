import pytest

from policy_agent.config import (
    ENV_CATALOG,
    ENV_LAKEBASE_URL,
    ENV_STORAGE_BACKEND,
    ENV_WAREHOUSE_ID,
    config_from_env,
    create_executor,
)
from policy_agent.errors import StorageError
from policy_agent.storage import BACKEND_LAKEBASE, BACKEND_UNITY_CATALOG
from policy_agent.storage.delta import DeltaSqlExecutor
from policy_agent.tagging import MANAGED_BY_TAG, managed_tags, parse_tags


def test_parse_tags_supports_json_and_csv():
    assert parse_tags('{"team": "platform"}') == {"team": "platform"}
    assert parse_tags("team=platform, env=prod") == {"team": "platform", "env": "prod"}
    assert parse_tags("") == {}


def test_managed_tags_always_includes_marker():
    tags = managed_tags({"team": "platform"})
    assert tags[MANAGED_BY_TAG] == "policy-agent"
    assert tags["team"] == "platform"


def test_config_from_env_builds_unity_catalog_storage_with_managed_tag():
    env = {
        ENV_STORAGE_BACKEND: BACKEND_UNITY_CATALOG,
        ENV_CATALOG: "governance",
        ENV_WAREHOUSE_ID: "wh-123",
        "POLICY_AGENT_TAGS": "team=platform",
        "POLICY_AGENT_NOTIFICATION_EMAILS": "a@x.com, b@x.com",
    }
    config = config_from_env(env)
    assert config.storage.backend == BACKEND_UNITY_CATALOG
    assert config.storage.catalog == "governance"
    assert config.storage.object_tags[MANAGED_BY_TAG] == "policy-agent"
    assert config.notification_emails == ("a@x.com", "b@x.com")


def test_create_executor_returns_delta_for_unity_catalog():
    config = config_from_env(
        {ENV_STORAGE_BACKEND: BACKEND_UNITY_CATALOG, ENV_CATALOG: "c", ENV_WAREHOUSE_ID: "wh"}
    )
    assert isinstance(create_executor(config, object()), DeltaSqlExecutor)


def test_create_executor_requires_warehouse_for_unity_catalog():
    config = config_from_env({ENV_STORAGE_BACKEND: BACKEND_UNITY_CATALOG, ENV_CATALOG: "c"})
    with pytest.raises(StorageError):
        create_executor(config, object())


def test_create_executor_requires_url_for_lakebase():
    config = config_from_env({ENV_STORAGE_BACKEND: BACKEND_LAKEBASE})
    with pytest.raises(StorageError):
        create_executor(config, object())


def test_create_executor_builds_lakebase_from_url():
    config = config_from_env(
        {ENV_STORAGE_BACKEND: BACKEND_LAKEBASE, ENV_LAKEBASE_URL: "sqlite+pysqlite:///:memory:"}
    )
    from policy_agent.storage.lakebase import LakebaseSqlExecutor

    assert isinstance(create_executor(config, object()), LakebaseSqlExecutor)
