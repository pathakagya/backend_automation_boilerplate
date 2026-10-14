"""Concrete PostgreSQL database adapter built on psycopg2-binary."""
from __future__ import annotations

import importlib
from typing import Any

from core.db_connection_manager import DatabaseConnection


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL implementation of the generic DatabaseConnection base class.

    Uses psycopg2's RealDictCursor so every row is returned as a plain dict,
    consistent with MySQLConnection's dictionary=True cursor behaviour.

    paramstyle = "format" — psycopg2 accepts %s positional placeholders, identical
    to mysql-connector-python, so db_helper / db_operations work unchanged.
    """

    paramstyle = "format"

    def _create_connection(self) -> Any:
        psycopg2 = importlib.import_module("psycopg2")

        connect_kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.user,
            "password": self.password,
        }

        connect_timeout = self.extra.get("connect_timeout")
        if connect_timeout is not None:
            connect_kwargs["connect_timeout"] = int(connect_timeout)

        sslmode = self.extra.get("sslmode")
        if sslmode:
            connect_kwargs["sslmode"] = sslmode

        conn = psycopg2.connect(**connect_kwargs)
        conn.autocommit = False
        return conn

    def _create_cursor(self) -> Any:
        """Return a RealDictCursor so rows come back as dicts, not tuples."""
        extras = importlib.import_module("psycopg2.extras")
        return self._conn.cursor(cursor_factory=extras.RealDictCursor)
