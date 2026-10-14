"""Contracts for project-owned database adapters.

The boilerplate intentionally does not import a database vendor driver. A
consuming project supplies an adapter that implements the connection contract
and installs the matching driver in its own dependency set.
"""
from __future__ import annotations

from typing import Any, ContextManager, Protocol, runtime_checkable


class DatabaseAdapterError(RuntimeError):
    """Base error for database adapter configuration or execution failures."""


class DatabaseAdapterUnavailable(DatabaseAdapterError):
    """Raised when DB-backed tests are requested without a usable adapter."""


@runtime_checkable
class DatabaseAdapter(Protocol):
    """Project-owned contract required by DB-backed integration and e2e tests.

    Implementations own vendor-specific connection creation, transaction
    semantics, schema metadata, seed/cleanup behavior, and optional diagnostics.
    Query values must be bound through the driver's parameter mechanism; callers
    must never interpolate untrusted values into SQL.
    """

    paramstyle: str

    def connect(self) -> DatabaseAdapter:
        """Open the adapter connection and return the adapter instance."""
        ...

    def cleanup(self) -> None:
        """Rollback active work and release all adapter-owned resources."""
        ...

    def execute(self, query: str, params: Any = None) -> Any:
        """Execute a parameterized statement and return a driver cursor/result."""
        ...

    def fetch_one(self, query: str, params: Any = None) -> Any | None:
        """Execute a parameterized query and return its first row, if present."""
        ...

    def fetch_all(self, query: str, params: Any = None) -> list[Any]:
        """Execute a parameterized query and return all rows."""
        ...

    def transaction(self) -> ContextManager[DatabaseAdapter]:
        """Return a context manager that commits or rolls back atomically."""
        ...

    def seed(self, plan: Any) -> Any:
        """Create project prerequisites and return cleanup metadata."""
        ...

    def cleanup_seed(self, metadata: Any) -> None:
        """Remove only rows created by a specific seed plan/run."""
        ...

    def diagnostics(self) -> dict[str, Any]:
        """Return safe, non-secret adapter capability and health information."""
        ...
