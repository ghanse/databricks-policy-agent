"""Lakebase (Postgres) executor backed by a SQLAlchemy engine.

The engine is supplied by the caller so credential handling (OAuth token refresh for
Lakebase, or a plain URL for local testing) stays outside the storage layer. Requires the
optional ``lakebase`` extra (``pip install databricks-policy-agent[lakebase]``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class LakebaseSqlExecutor:
    """Runs SQL against a Lakebase Postgres database through a SQLAlchemy engine."""

    def __init__(self, engine: Engine) -> None:
        """Initialises the executor.

        Args:
            engine: A SQLAlchemy engine connected to the target Postgres database.
        """
        self._engine = engine

    def execute(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        """Executes a statement that returns no rows.

        Args:
            statement: SQL text with ``:name`` parameter markers.
            parameters: Named parameter values, if any.
        """
        with self._engine.begin() as connection:
            connection.execute(text(statement), dict(parameters or {}))

    def query(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Executes a query and returns its rows as column-keyed mappings.

        Args:
            statement: SQL text with ``:name`` parameter markers.
            parameters: Named parameter values, if any.

        Returns:
            The result rows with native Python values.
        """
        with self._engine.connect() as connection:
            result = connection.execute(text(statement), dict(parameters or {}))
            return [dict(row._mapping) for row in result]
