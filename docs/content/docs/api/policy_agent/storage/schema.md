---
sidebar_label: schema
title: policy_agent.storage.schema
---

Table definitions and dialect-aware SQL builders for both storage backends.

Everything here is a pure function of a `StorageConfig`: it produces SQL text and
parameter mappings but never executes anything. The same table set is created for Unity
Catalog Delta and Lakebase Postgres, differing only in type names, tagging syntax, and
upsert strategy (delete-then-insert, which both dialects support without vendor extensions).

## ColumnType Objects

```python
class ColumnType(str, Enum)
```

A portable column type mapped to each backend's concrete SQL type.

## Column Objects

```python
@dataclass(frozen=True)
class Column()
```

A single table column.

**Attributes**:

- `name` - Column name.
- `type` - Portable column type.
- `nullable` - Whether the column accepts ``NULL``.

## Table Objects

```python
@dataclass(frozen=True)
class Table()
```

A logical table definition shared by both backends.

**Attributes**:

- `logical_name` - Unqualified table name (prefixed and qualified at build time).
- `columns` - Ordered column definitions.
- `primary_key` - Columns identifying a row for upsert/delete; empty for append-only tables.

#### create\_namespace\_statements

```python
def create_namespace_statements(config: StorageConfig,
                                include_catalog: bool = True) -> list[str]
```

Builds the statements that create the catalog/schema and apply object tags.

**Arguments**:

- `config` - The storage configuration.
- `include_catalog` - Whether to emit ``CREATE CATALOG`` (Unity Catalog only). Skip it
  when the catalog already exists: accounts with Default Storage reject
  ``CREATE CATALOG`` for an existing catalog because it has no explicit location.
  

**Returns**:

  Ordered SQL statements to create the namespace, safe to run repeatedly.

#### create\_table\_statements

```python
def create_table_statements(config: StorageConfig) -> list[str]
```

Builds ``CREATE TABLE`` (and tag) statements for every table.

**Arguments**:

- `config` - The storage configuration.
  

**Returns**:

  Ordered SQL statements creating all tables, safe to run repeatedly.

#### insert\_statement

```python
def insert_statement(config: StorageConfig, table_name: str,
                     row: dict[str, Any]) -> tuple[str, dict[str, Any]]
```

Builds a parameterized ``INSERT`` for one row.

**Arguments**:

- `config` - The storage configuration.
- `table_name` - Logical table name.
- `row` - Column-name-to-value mapping to insert.
  

**Returns**:

  The SQL statement and its named parameter mapping.

#### delete\_statement

```python
def delete_statement(config: StorageConfig, table_name: str,
                     key: dict[str, Any]) -> tuple[str, dict[str, Any]]
```

Builds a parameterized ``DELETE`` matching the given key columns.

**Arguments**:

- `config` - The storage configuration.
- `table_name` - Logical table name.
- `key` - Column-name-to-value mapping identifying the rows to delete.
  

**Returns**:

  The SQL statement and its named parameter mapping.

#### select\_statement

```python
def select_statement(
        config: StorageConfig,
        table_name: str,
        where: dict[str, Any] | None = None,
        order_by: str | None = None) -> tuple[str, dict[str, Any]]
```

Builds a parameterized ``SELECT *`` with an optional equality filter and ordering.

**Arguments**:

- `config` - The storage configuration.
- `table_name` - Logical table name.
- `where` - Optional column-name-to-value equality filter.
- `order_by` - Optional ``ORDER BY`` clause body (e.g. ``"created_at DESC"``).
  

**Returns**:

  The SQL statement and its named parameter mapping.

