"""Unity Catalog Delta executor backed by the SQL Statement Execution API.

Statements run on a serverless or classic SQL warehouse. Every result value comes back as a
string; `policy_agent.storage.records` readers coerce them to their typed form.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any

from databricks.sdk.service.sql import StatementParameterListItem, StatementState

from policy_agent.errors import StorageError

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

_TERMINAL_STATES = {
    StatementState.SUCCEEDED,
    StatementState.FAILED,
    StatementState.CANCELED,
    StatementState.CLOSED,
}


class DeltaSqlExecutor:
    """Runs SQL against a Databricks SQL warehouse via the Statement Execution API."""

    def __init__(
        self,
        workspace_client: WorkspaceClient,
        warehouse_id: str,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        """Initialises the executor.

        Args:
            workspace_client: An authenticated Databricks workspace client.
            warehouse_id: Identifier of the SQL warehouse to run statements on.
            poll_interval_seconds: Delay between polls while a statement is running.
        """
        self._workspace_client = workspace_client
        self._warehouse_id = warehouse_id
        self._poll_interval_seconds = poll_interval_seconds

    def execute(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        """Executes a statement that returns no rows.

        Args:
            statement: SQL text with ``:name`` parameter markers.
            parameters: Named parameter values, if any.
        """
        self._run(statement, parameters)

    def query(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Executes a query and returns its rows as column-keyed mappings.

        Args:
            statement: SQL text with ``:name`` parameter markers.
            parameters: Named parameter values, if any.

        Returns:
            The result rows, with every value as a string or ``None``.
        """
        response = self._run(statement, parameters)
        manifest = response.manifest
        result = response.result
        if manifest is None or manifest.schema is None or result is None:
            return []
        column_names = [column.name for column in (manifest.schema.columns or [])]
        return [dict(zip(column_names, row, strict=False)) for row in (result.data_array or [])]

    def _run(self, statement: str, parameters: Mapping[str, Any] | None) -> Any:
        response = self._workspace_client.statement_execution.execute_statement(
            statement=statement,
            warehouse_id=self._warehouse_id,
            parameters=_to_statement_parameters(parameters),
            wait_timeout="50s",
        )
        response = self._await_completion(response)
        state = response.status.state if response.status else None
        if state is not StatementState.SUCCEEDED:
            message = (
                response.status.error.message
                if response.status and response.status.error
                else state
            )
            raise StorageError(f"Statement failed ({state}): {message}")
        return response

    def _await_completion(self, response: Any) -> Any:
        while response.status and response.status.state not in _TERMINAL_STATES:
            time.sleep(self._poll_interval_seconds)
            response = self._workspace_client.statement_execution.get_statement(
                response.statement_id
            )
        return response


def _to_statement_parameters(
    parameters: Mapping[str, Any] | None,
) -> list[StatementParameterListItem] | None:
    if not parameters:
        return None
    return [_to_statement_parameter(name, value) for name, value in parameters.items()]


def _to_statement_parameter(name: str, value: Any) -> StatementParameterListItem:
    if value is None:
        return StatementParameterListItem(name=name, value=None)
    if isinstance(value, bool):
        return StatementParameterListItem(name=name, value=str(value).lower(), type="BOOLEAN")
    if isinstance(value, int):
        return StatementParameterListItem(name=name, value=str(value), type="BIGINT")
    if isinstance(value, float):
        return StatementParameterListItem(name=name, value=str(value), type="DOUBLE")
    if isinstance(value, datetime):
        return StatementParameterListItem(name=name, value=value.isoformat(), type="TIMESTAMP")
    return StatementParameterListItem(name=name, value=str(value), type="STRING")
