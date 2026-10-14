"""
DatabaseConnection: Abstract base class for database connections.

Projects subclass this and provide their driver implementation.

Example (Oracle):
    import cx_Oracle

    class OracleConnection(DatabaseConnection):
        paramstyle = "numeric"  # cx_Oracle/oracledb positional binds: :1, :2, ...

        def _create_connection(self):
            dsn = cx_Oracle.makedsn(self.host, self.port, service_name=self.database)
            return cx_Oracle.connect(self.user, self.password, dsn)

        def _create_cursor(self):
            return self._conn.cursor()

Example (MSSQL via pyodbc):
    import pyodbc

    class MSSQLConnection(DatabaseConnection):
        paramstyle = "qmark"  # pyodbc binds: ?, ?, ...

        def _create_connection(self):
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.host},{self.port};"
                f"DATABASE={self.database};"
                f"UID={self.user};PWD={self.password}"
            )
            return pyodbc.connect(conn_str)

        def _create_cursor(self):
            return self._conn.cursor()

"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Generator, Optional

from core.shared_utils import get_allure_module, attach_json_to_allure


class DatabaseConnectionError(Exception):
    """Raised when a database operation fails."""


class DatabaseConnection(ABC):
    """
    Abstract base for all database connections.

    Provides:
        - connect / disconnect lifecycle
        - execute, fetch_one, fetch_all query helpers
        - Transaction context manager (auto-rollback on exceptions)
        - Automatic cleanup hook for pytest fixtures

    Projects only need to implement _create_connection() and _create_cursor().
    """

    paramstyle: str = "format"

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        **extra: Any,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.database = database
        self.user = user
        self.password = password
        self.extra = extra

        self._conn: Any = None
        self._cursor: Any = None
        self._in_transaction: bool = False

    # ------------------------------------------------------------------ #
    # Abstract interface — must be implemented by each driver subclass
    # ------------------------------------------------------------------ #

    @abstractmethod
    def _create_connection(self) -> Any:
        """Create and return a raw driver connection object."""

    @abstractmethod
    def _create_cursor(self) -> Any:
        """Create and return a cursor from the active connection."""

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def connect(self) -> "DatabaseConnection":
        """Open the database connection. Returns self for chaining."""
        if self._conn is not None:
            return self

        try:
            self._conn = self._create_connection()
            self._cursor = self._create_cursor()
        except Exception as exc:
            raise DatabaseConnectionError(
                f"Failed to connect to {self.host}:{self.port}/{self.database}: {exc}"
            ) from exc
        return self

    def disconnect(self) -> None:
        """Close cursor and connection, rolling back any open transaction."""
        if self._in_transaction:
            self._safe_rollback()

        if self._cursor is not None:
            try:
                self._cursor.close()
            except Exception:
                pass
            self._cursor = None

        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ------------------------------------------------------------------ #
    # Query helpers
    # ------------------------------------------------------------------ #

    def execute(self, query: str, params: Optional[Any] = None) -> Any:
        """Execute a statement. Returns the cursor (for rowcount / lastrowid)."""
        self._ensure_connected()
        try:
            if params is not None:
                self._cursor.execute(query, params)
            else:
                self._cursor.execute(query)
            self._attach_query(query=query, params=params)
            return self._cursor
        except Exception as exc:
            raise DatabaseConnectionError(f"Query execution failed: {exc}") from exc

    def fetch_one(self, query: str, params: Optional[Any] = None) -> Optional[Any]:
        """Execute a SELECT and return the first row, or None."""
        self.execute(query, params)
        row = self._cursor.fetchone()
        # Drain any remaining rows so the connection doesn't hold an unread result.
        # mysql-connector-python (C extension) raises InternalError on commit() or the
        # next execute() if rows from a previous SELECT are still pending on the cursor.
        try:
            self._cursor.fetchall()
        except Exception:
            pass
        self._attach_result("fetch_one", row)
        return row

    def fetch_all(self, query: str, params: Optional[Any] = None) -> list[Any]:
        """Execute a SELECT and return all rows."""
        self.execute(query, params)
        rows = self._cursor.fetchall()
        self._attach_result("fetch_all", {"count": len(rows), "rows": rows[:20]})
        return rows

    def commit(self) -> None:
        """Commit the current transaction."""
        self._ensure_connected()
        self._conn.commit()
        self._in_transaction = False

    def rollback(self) -> None:
        """Roll back the current transaction."""
        self._safe_rollback()

    # ------------------------------------------------------------------ #
    # Transaction context manager
    # ------------------------------------------------------------------ #

    @contextmanager
    def transaction(self) -> Generator["DatabaseConnection", None, None]:
        """
        Context manager that auto-commits on success and rolls back on any exception.

        Usage:
            with db.transaction():
                db.execute("INSERT INTO ...")
                db.execute("UPDATE ...")
            # committed here

            with db.transaction():
                db.execute("DELETE FROM ...")
                raise SomeError()
            # rolled back here
        """
        self._ensure_connected()
        self._in_transaction = True
        try:
            yield self
            self.commit()
        except Exception:
            self._safe_rollback()
            raise

    # ------------------------------------------------------------------ #
    # Pytest integration
    # ------------------------------------------------------------------ #

    def cleanup(self) -> None:
        """
        Called by pytest fixtures in teardown.
        Rolls back any open transaction and disconnects.
        """
        if self._in_transaction:
            self._safe_rollback()
        self.disconnect()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _ensure_connected(self) -> None:
        """Raise a configuration error when a query lacks an active connection."""
        if self._conn is None:
            raise DatabaseConnectionError(
                "No active connection. Call connect() before executing queries."
            )

    def _safe_rollback(self) -> None:
        """Rollback best-effort and always clear the transaction flag."""
        try:
            if self._conn is not None:
                self._conn.rollback()
        except Exception:
            pass
        finally:
            self._in_transaction = False

    def _attach_query(self, query: str, params: Optional[Any]) -> None:
        """Attach a sanitized query and bound parameters to Allure when enabled."""
        payload = {"query": query, "params": self._sanitize_for_report(params)}
        attach_json_to_allure(payload, "DB Query")

    def _attach_result(self, op: str, result: Any) -> None:
        """Attach a sanitized DB result summary to Allure when enabled."""
        payload = {"operation": op, "result": self._sanitize_for_report(result)}
        attach_json_to_allure(payload, f"DB Result: {op}")

    @staticmethod
    def _sanitize_for_report(value: Any) -> Any:
        """Redact likely credentials before DB evidence is attached to Allure."""
        secret_names = ("password", "token", "secret", "api_key", "authorization")
        if isinstance(value, dict):
            return {
                key: (
                    "<redacted>"
                    if any(name in str(key).lower() for name in secret_names)
                    else DatabaseConnection._sanitize_for_report(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [DatabaseConnection._sanitize_for_report(item) for item in value]
        return value

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "DatabaseConnection":
        """
        Factory method: create an instance from a config dict.

        The dict should contain at minimum:
            host, port, name (database name), user, password

        Any extra keys are passed through as kwargs for driver-specific options.
        """
        required = {"host", "port", "name", "user", "password"}
        missing = required - config.keys()
        if missing:
            raise DatabaseConnectionError(
                f"Missing required database config keys: {missing}"
            )
        return cls(
            host=config["host"],
            port=config["port"],
            database=config["name"],
            user=config["user"],
            password=config["password"],
            **{k: v for k, v in config.items() if k not in required},
        )

    def __repr__(self) -> str:
        status = "connected" if self._conn else "disconnected"
        return f"{self.__class__.__name__}({self.user}@{self.host}:{self.port}/{self.database} [{status}])"
