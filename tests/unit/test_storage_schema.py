import pytest

from policy_agent.errors import StorageError
from policy_agent.storage import BACKEND_LAKEBASE, BACKEND_UNITY_CATALOG, StorageConfig, schema


def _uc():
    return StorageConfig(
        backend=BACKEND_UNITY_CATALOG,
        catalog="governance",
        schema="policy_agent",
        object_tags={"team": "platform"},
    )


def _pg():
    return StorageConfig(backend=BACKEND_LAKEBASE, schema="policy_agent", object_tags={"team": "x"})


def test_unity_catalog_requires_catalog():
    with pytest.raises(StorageError):
        StorageConfig(backend=BACKEND_UNITY_CATALOG)


def test_unknown_backend_rejected():
    with pytest.raises(StorageError):
        StorageConfig(backend="sqlite")


def test_table_identifier_qualification():
    assert _uc().table_identifier("policies") == "governance.policy_agent.policies"
    assert _pg().table_identifier("policies") == "policy_agent.policies"
    prefixed = StorageConfig(backend=BACKEND_LAKEBASE, schema="s", table_prefix="pa_")
    assert prefixed.table_identifier("scans") == "s.pa_scans"


def test_unity_catalog_namespace_and_tags():
    statements = schema.create_namespace_statements(_uc())
    assert "CREATE CATALOG IF NOT EXISTS governance" in statements
    assert "CREATE SCHEMA IF NOT EXISTS governance.policy_agent" in statements
    assert any("SET TAGS ('team' = 'platform')" in s for s in statements)


def test_postgres_namespace_uses_comment_for_tags():
    statements = schema.create_namespace_statements(_pg())
    assert "CREATE SCHEMA IF NOT EXISTS policy_agent" in statements
    assert any(s.startswith("COMMENT ON SCHEMA policy_agent IS") for s in statements)


def test_unity_catalog_table_ddl_types_and_tagging():
    statements = schema.create_table_statements(_uc())
    policies_ddl = next(
        s for s in statements if "CREATE TABLE IF NOT EXISTS governance.policy_agent.policies" in s
    )
    assert "name STRING NOT NULL" in policies_ddl
    assert "version BIGINT" in policies_ddl
    assert any("ALTER TABLE governance.policy_agent.policies SET TAGS" in s for s in statements)


def test_postgres_table_ddl_has_primary_key_and_text():
    statements = schema.create_table_statements(_pg())
    policies_ddl = next(
        s for s in statements if "CREATE TABLE IF NOT EXISTS policy_agent.policies" in s
    )
    assert "name TEXT NOT NULL" in policies_ddl
    assert "PRIMARY KEY (name)" in policies_ddl
    role_ddl = next(
        s for s in statements if "policy_agent.role_mappings" in s and s.startswith("CREATE")
    )
    assert "PRIMARY KEY (group_name, role)" in role_ddl


def test_insert_delete_select_builders():
    config = _pg()
    insert_sql, insert_params = schema.insert_statement(
        config, "policies", {"name": "p", "version": 1}
    )
    assert (
        insert_sql == "INSERT INTO policy_agent.policies (name, version) VALUES (:name, :version)"
    )
    assert insert_params == {"name": "p", "version": 1}

    delete_sql, delete_params = schema.delete_statement(config, "policies", {"name": "p"})
    assert delete_sql == "DELETE FROM policy_agent.policies WHERE name = :name"
    assert delete_params == {"name": "p"}

    select_sql, select_params = schema.select_statement(
        config, "findings", where={"scan_id": "s1"}, order_by="created_at DESC"
    )
    assert (
        select_sql
        == "SELECT * FROM policy_agent.findings WHERE scan_id = :scan_id ORDER BY created_at DESC"
    )
    assert select_params == {"scan_id": "s1"}
