---
sidebar_label: config
title: policy_agent.storage.config
---

Storage placement configuration for either Unity Catalog Delta or Lakebase Postgres.

A :class:`StorageConfig` says *where* policy-agent state lives and *how objects are tagged*;
it does not hold connection credentials — those belong to the executor. The same config type
drives both backends so the rest of the framework is storage-agnostic.

## StorageConfig Objects

```python
@dataclass(frozen=True)
class StorageConfig()
```

Where policy-agent tables live and which tags every created object carries.

**Attributes**:

- `backend` - Either ``&quot;uc&quot;`` (Unity Catalog Delta) or ``&quot;lakebase&quot;`` (Postgres).
- `schema` - Schema (Postgres) or UC schema name that holds the tables.
- `catalog` - Unity Catalog catalog name; required when ``backend`` is ``&quot;uc&quot;``.
- ``1 - Optional prefix applied to every table name to avoid collisions.
- ``2 - Tags stamped onto created schemas/tables and onto every stored row.

#### is\_unity\_catalog

```python
@property
def is_unity_catalog() -> bool
```

Whether this config targets Unity Catalog Delta storage.

#### qualified\_schema

```python
@property
def qualified_schema() -> str
```

The fully qualified schema name (``catalog.schema`` for UC, ``schema`` otherwise).

#### table\_identifier

```python
def table_identifier(logical_name: str) -> str
```

Return the fully qualified identifier for a logical table name.

**Arguments**:

- `logical_name` - The table&#x27;s logical name (e.g. ``policies``).
  

**Returns**:

  The qualified, prefixed identifier used in SQL statements.

