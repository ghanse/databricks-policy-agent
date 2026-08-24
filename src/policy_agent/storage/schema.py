"""Table definitions and dialect-aware SQL builders for both storage backends.

Everything here is a pure function of a :class:`StorageConfig`: it produces SQL text and
parameter mappings but never executes anything. The same table set is created for Unity
Catalog Delta and Lakebase Postgres, differing only in type names, tagging syntax, and
upsert strategy (delete-then-insert, which both dialects support without vendor extensions).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from policy_agent.storage.config import StorageConfig


class ColumnType(str, Enum):
    """A portable column type mapped to each backend's concrete SQL type."""

    STRING = "string"
    LONG = "long"
    DOUBLE = "double"
    BOOL = "bool"
    TIMESTAMP = "timestamp"


@dataclass(frozen=True)
class Column:
    """A single table column.

    Attributes:
        name: Column name.
        type: Portable column type.
        nullable: Whether the column accepts ``NULL``.
    """

    name: str
    type: ColumnType
    nullable: bool = True


@dataclass(frozen=True)
class Table:
    """A logical table definition shared by both backends.

    Attributes:
        logical_name: Unqualified table name (prefixed and qualified at build time).
        columns: Ordered column definitions.
        primary_key: Columns identifying a row for upsert/delete; empty for append-only tables.
    """

    logical_name: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...] = field(default_factory=tuple)


_S = ColumnType.STRING
_L = ColumnType.LONG
_B = ColumnType.BOOL
_T = ColumnType.TIMESTAMP


TABLES: tuple[Table, ...] = (
    Table(
        "policies",
        (
            Column("name", _S, nullable=False),
            Column("resource_type", _S),
            Column("effect", _S),
            Column("enforcement", _S),
            Column("status", _S),
            Column("version", _L),
            Column("description", _S),
            Column("remediation", _S),
            Column("rule", _S),
            Column("match", _S),
            Column("object_tags", _S),
            Column("updated_at", _T),
        ),
        primary_key=("name",),
    ),
    Table(
        "policy_versions",
        (
            Column("name", _S, nullable=False),
            Column("version", _L, nullable=False),
            Column("definition", _S),
            Column("actor", _S),
            Column("created_at", _T),
        ),
    ),
    Table(
        "approval_events",
        (
            Column("event_id", _S, nullable=False),
            Column("policy_name", _S),
            Column("from_status", _S),
            Column("to_status", _S),
            Column("actor", _S),
            Column("note", _S),
            Column("created_at", _T),
        ),
    ),
    Table(
        "scans",
        (
            Column("scan_id", _S, nullable=False),
            Column("started_at", _T),
            Column("finished_at", _T),
            Column("policy_names", _S),
            Column("resource_types", _S),
            Column("evaluated", _L),
            Column("compliant", _L),
            Column("violations", _L),
            Column("summary", _S),
            Column("triggered_by", _S),
            Column("object_tags", _S),
        ),
        primary_key=("scan_id",),
    ),
    Table(
        "findings",
        (
            Column("finding_id", _S, nullable=False),
            Column("scan_id", _S),
            Column("policy_name", _S),
            Column("resource_type", _S),
            Column("resource_id", _S),
            Column("resource_name", _S),
            Column("compliant", _B),
            Column("effect", _S),
            Column("enforcement", _S),
            Column("message", _S),
            Column("remediation", _S),
            Column("owner", _S),
            Column("object_tags", _S),
            Column("created_at", _T),
        ),
    ),
    Table(
        "remediations",
        (
            Column("remediation_id", _S, nullable=False),
            Column("finding_id", _S),
            Column("scan_id", _S),
            Column("policy_name", _S),
            Column("resource_type", _S),
            Column("resource_id", _S),
            Column("resource_name", _S),
            Column("enforcement", _S),
            Column("status", _S),
            Column("assignee", _S),
            Column("note", _S),
            Column("object_tags", _S),
            Column("opened_at", _T),
            Column("updated_at", _T),
        ),
        primary_key=("remediation_id",),
    ),
    Table(
        "schedules",
        (
            Column("schedule_id", _S, nullable=False),
            Column("name", _S),
            Column("cron", _S),
            Column("timezone", _S),
            Column("policy_names", _S),
            Column("resource_types", _S),
            Column("paused", _B),
            Column("object_tags", _S),
            Column("updated_at", _T),
        ),
        primary_key=("schedule_id",),
    ),
    Table(
        "role_mappings",
        (
            Column("group_name", _S, nullable=False),
            Column("role", _S, nullable=False),
            Column("object_tags", _S),
            Column("updated_at", _T),
        ),
        primary_key=("group_name", "role"),
    ),
)


TABLES_BY_NAME: dict[str, Table] = {table.logical_name: table for table in TABLES}


_UNITY_CATALOG_TYPES = {
    ColumnType.STRING: "STRING",
    ColumnType.LONG: "BIGINT",
    ColumnType.DOUBLE: "DOUBLE",
    ColumnType.BOOL: "BOOLEAN",
    ColumnType.TIMESTAMP: "TIMESTAMP",
}
_POSTGRES_TYPES = {
    ColumnType.STRING: "TEXT",
    ColumnType.LONG: "BIGINT",
    ColumnType.DOUBLE: "DOUBLE PRECISION",
    ColumnType.BOOL: "BOOLEAN",
    ColumnType.TIMESTAMP: "TIMESTAMPTZ",
}


def create_namespace_statements(config: StorageConfig) -> list[str]:
    """Build the statements that create the catalog/schema and apply object tags.

    Args:
        config: The storage configuration.

    Returns:
        Ordered SQL statements to create the namespace, safe to run repeatedly.
    """
    statements: list[str] = []
    if config.is_unity_catalog:
        statements.append(f"CREATE CATALOG IF NOT EXISTS {config.catalog}")
        statements.append(f"CREATE SCHEMA IF NOT EXISTS {config.qualified_schema}")
        tags = _unity_catalog_tag_clause(config.object_tags)
        if tags:
            statements.append(f"ALTER SCHEMA {config.qualified_schema} SET TAGS ({tags})")
    else:
        statements.append(f"CREATE SCHEMA IF NOT EXISTS {config.schema}")
        if config.object_tags:
            comment = _sql_string_literal(json.dumps(dict(config.object_tags), sort_keys=True))
            statements.append(f"COMMENT ON SCHEMA {config.schema} IS {comment}")
    return statements


def create_table_statements(config: StorageConfig) -> list[str]:
    """Build ``CREATE TABLE`` (and tag) statements for every table.

    Args:
        config: The storage configuration.

    Returns:
        Ordered SQL statements creating all tables, safe to run repeatedly.
    """
    return [statement for table in TABLES for statement in _create_table(config, table)]


def insert_statement(
    config: StorageConfig, table_name: str, row: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Build a parameterized ``INSERT`` for one row.

    Args:
        config: The storage configuration.
        table_name: Logical table name.
        row: Column-name-to-value mapping to insert.

    Returns:
        The SQL statement and its named parameter mapping.
    """
    columns = list(row)
    placeholders = ", ".join(f":{column}" for column in columns)
    identifier = config.table_identifier(table_name)
    sql = f"INSERT INTO {identifier} ({', '.join(columns)}) VALUES ({placeholders})"
    return sql, dict(row)


def delete_statement(
    config: StorageConfig, table_name: str, key: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Build a parameterized ``DELETE`` matching the given key columns.

    Args:
        config: The storage configuration.
        table_name: Logical table name.
        key: Column-name-to-value mapping identifying the rows to delete.

    Returns:
        The SQL statement and its named parameter mapping.
    """
    identifier = config.table_identifier(table_name)
    predicate = " AND ".join(f"{column} = :{column}" for column in key)
    return f"DELETE FROM {identifier} WHERE {predicate}", dict(key)


def select_statement(
    config: StorageConfig,
    table_name: str,
    where: dict[str, Any] | None = None,
    order_by: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build a parameterized ``SELECT *`` with an optional equality filter and ordering.

    Args:
        config: The storage configuration.
        table_name: Logical table name.
        where: Optional column-name-to-value equality filter.
        order_by: Optional ``ORDER BY`` clause body (e.g. ``"created_at DESC"``).

    Returns:
        The SQL statement and its named parameter mapping.
    """
    identifier = config.table_identifier(table_name)
    sql = f"SELECT * FROM {identifier}"
    parameters: dict[str, Any] = {}
    if where:
        predicate = " AND ".join(f"{column} = :{column}" for column in where)
        sql += f" WHERE {predicate}"
        parameters = dict(where)
    if order_by:
        sql += f" ORDER BY {order_by}"
    return sql, parameters


def _create_table(config: StorageConfig, table: Table) -> list[str]:
    identifier = config.table_identifier(table.logical_name)
    types = _UNITY_CATALOG_TYPES if config.is_unity_catalog else _POSTGRES_TYPES
    column_definitions = [
        f"{column.name} {types[column.type]}{'' if column.nullable else ' NOT NULL'}"
        for column in table.columns
    ]
    if not config.is_unity_catalog and table.primary_key:
        column_definitions.append(f"PRIMARY KEY ({', '.join(table.primary_key)})")
    body = ", ".join(column_definitions)
    statements = [f"CREATE TABLE IF NOT EXISTS {identifier} ({body})"]
    statements.extend(_table_tag_statements(config, identifier))
    return statements


def _table_tag_statements(config: StorageConfig, identifier: str) -> list[str]:
    if not config.object_tags:
        return []
    if config.is_unity_catalog:
        tags = _unity_catalog_tag_clause(config.object_tags)
        return [f"ALTER TABLE {identifier} SET TAGS ({tags})"]
    comment = _sql_string_literal(json.dumps(dict(config.object_tags), sort_keys=True))
    return [f"COMMENT ON TABLE {identifier} IS {comment}"]


def _unity_catalog_tag_clause(tags: Any) -> str:
    return ", ".join(
        f"{_sql_string_literal(key)} = {_sql_string_literal(value)}"
        for key, value in sorted(dict(tags).items())
    )


def _sql_string_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"
