"""Storage placement configuration for either Unity Catalog Delta or Lakebase Postgres.

A `StorageConfig` says *where* policy-agent state lives and *how objects are tagged*;
it does not hold connection credentials — those belong to the executor. The same config type
drives both backends so the rest of the framework is storage-agnostic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from policy_agent.errors import StorageError

BACKEND_UNITY_CATALOG = "uc"
BACKEND_LAKEBASE = "lakebase"
SUPPORTED_BACKENDS = (BACKEND_UNITY_CATALOG, BACKEND_LAKEBASE)


@dataclass(frozen=True)
class StorageConfig:
    """Where policy-agent tables live and which tags every created object carries.

    Attributes:
        backend: Either ``"uc"`` (Unity Catalog Delta) or ``"lakebase"`` (Postgres).
        schema: Schema (Postgres) or UC schema name that holds the tables.
        catalog: Unity Catalog catalog name; required when ``backend`` is ``"uc"``.
        table_prefix: Optional prefix applied to every table name to avoid collisions.
        object_tags: Tags stamped onto created schemas/tables and onto every stored row.
    """

    backend: str
    schema: str = "policy_agent"
    catalog: str | None = None
    table_prefix: str = ""
    object_tags: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.backend not in SUPPORTED_BACKENDS:
            raise StorageError(
                f"Unsupported storage backend {self.backend!r}; expected one of "
                f"{SUPPORTED_BACKENDS}."
            )
        if self.backend == BACKEND_UNITY_CATALOG and not self.catalog:
            raise StorageError("Unity Catalog storage requires a 'catalog'.")

    @property
    def is_unity_catalog(self) -> bool:
        """Whether this config targets Unity Catalog Delta storage."""
        return self.backend == BACKEND_UNITY_CATALOG

    @property
    def qualified_schema(self) -> str:
        """The fully qualified schema name (``catalog.schema`` for UC, ``schema`` otherwise)."""
        if self.is_unity_catalog:
            return f"{self.catalog}.{self.schema}"
        return self.schema

    def table_identifier(self, logical_name: str) -> str:
        """Returns the fully qualified identifier for a logical table name.

        Args:
            logical_name: The table's logical name (e.g. ``policies``).

        Returns:
            The qualified, prefixed identifier used in SQL statements.
        """
        return f"{self.qualified_schema}.{self.table_prefix}{logical_name}"
