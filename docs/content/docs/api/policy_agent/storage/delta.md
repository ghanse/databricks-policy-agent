---
sidebar_label: delta
title: policy_agent.storage.delta
---

Unity Catalog Delta executor backed by the SQL Statement Execution API.

Statements run on a serverless or classic SQL warehouse. Every result value comes back as a
string; `policy_agent.storage.records` readers coerce them to their typed form.

## DeltaSqlExecutor Objects

```python
class DeltaSqlExecutor()
```

Runs SQL against a Databricks SQL warehouse via the Statement Execution API.

#### \_\_init\_\_

```python
def __init__(workspace_client: WorkspaceClient,
             warehouse_id: str,
             poll_interval_seconds: float = 1.0) -> None
```

Initialises the executor.

**Arguments**:

- `workspace_client` - An authenticated Databricks workspace client.
- `warehouse_id` - Identifier of the SQL warehouse to run statements on.
- `poll_interval_seconds` - Delay between polls while a statement is running.

#### execute

```python
def execute(statement: str,
            parameters: Mapping[str, Any] | None = None) -> None
```

Executes a statement that returns no rows.

**Arguments**:

- `statement` - SQL text with ``:name`` parameter markers.
- `parameters` - Named parameter values, if any.

#### query

```python
def query(statement: str,
          parameters: Mapping[str, Any] | None = None) -> list[dict[str, Any]]
```

Executes a query and returns its rows as column-keyed mappings.

**Arguments**:

- `statement` - SQL text with ``:name`` parameter markers.
- `parameters` - Named parameter values, if any.
  

**Returns**:

  The result rows, with every value as a string or ``None``.

