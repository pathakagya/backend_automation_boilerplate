"""Concrete Oracle database adapter built on oracledb (thin mode)."""
from __future__ import annotations

import importlib
from typing import Any

from core.db_connection_manager import DatabaseConnection


class OracleConnection(DatabaseConnection):
    """Oracle implementation of the generic DatabaseConnection base class.

    Uses the modern `oracledb` driver in thin mode — no Oracle Instant Client
    installation required on dev machines or CI runners.

    paramstyle = "numeric" — oracledb uses :1, :2, ... positional placeholders
    with a list/tuple of values, consistent with the positional bind pattern used
    by db_helper / db_operations.

    oracledb cursors return tuple rows by default. Dict rows are produced by
    setting cursor.rowfactory after each execute() call (cursor.description is
    only populated after execute, not at cursor creation time).
    """

    paramstyle = "numeric"

    def _create_connection(self) -> Any:
        oracledb = importlib.import_module("oracledb")

        connect_timeout = self.extra.get("connect_timeout")
        if connect_timeout is not None:
            oracledb.defaults.tcp_connect_timeout = float(connect_timeout)

        dsn = f"{self.host}:{self.port}/{self.database}"
        return oracledb.connect(user=self.user, password=self.password, dsn=dsn)

    def _create_cursor(self) -> Any:
        return self._conn.cursor()

    def execute(self, query: str, params: Any = None) -> Any:
        """Run query via base class, then wire rowfactory for dict rows."""
        cursor = super().execute(query, params)
        if cursor.description:
            col_names = [d[0].lower() for d in cursor.description]
            cursor.rowfactory = lambda *args: dict(zip(col_names, args))
        return cursor
