---
sidebar_label: lakebase
title: policy_agent.storage.lakebase
---

Lakebase (Postgres) executor backed by a SQLAlchemy engine.

The engine is supplied by the caller so credential handling (OAuth token refresh for
Lakebase, or a plain URL for local testing) stays outside the storage layer. Requires the
optional ``lakebase`` extra (``pip install databricks-policy-agent[lakebase]``).

## LakebaseSqlExecutor Objects

```python
class LakebaseSqlExecutor()
```

Runs SQL against a Lakebase Postgres database through a SQLAlchemy engine.

#### \_\_init\_\_

```python
def __init__(engine: Engine) -> None
```

Initialise the executor.

**Arguments**:

- `engine` - A SQLAlchemy engine connected to the target Postgres database.

#### execute

```python
def execute(statement: str,
            parameters: Mapping[str, Any] | None = None) -> None
```

Execute a statement that returns no rows.

**Arguments**:

- `statement` - SQL text with ``:name`` parameter markers.
- `parameters` - Named parameter values, if any.

#### query

```python
def query(statement: str,
          parameters: Mapping[str, Any] | None = None) -> list[dict[str, Any]]
```

Execute a query and return its rows as column-keyed mappings.

**Arguments**:

- `statement` - SQL text with ``:name`` parameter markers.
- `parameters` - Named parameter values, if any.
  

**Returns**:

  The result rows with native Python values.

