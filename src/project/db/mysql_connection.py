"""Concrete MySQL database adapter built on mysql-connector-python."""
from __future__ import annotations

import importlib
from typing import Any

from core.db_connection_manager import DatabaseConnection


class MySQLConnection(DatabaseConnection):
    """MySQL implementation of the generic DatabaseConnection base class."""

    def _create_connection(self) -> Any:
        """Create a non-autocommit MySQL connection using project config."""
        mysql_connector = importlib.import_module("mysql.connector")

        connect_kwargs = {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "autocommit": False,
        }

        connect_timeout = self.extra.get("connect_timeout")
        if connect_timeout is not None:
            connect_kwargs["connection_timeout"] = int(connect_timeout)

        ssl_disabled = self.extra.get("ssl_disabled")
        if ssl_disabled is not None:
            connect_kwargs["ssl_disabled"] = str(ssl_disabled).lower() in ("true", "1", "yes")

        charset = self.extra.get("charset")
        if charset:
            connect_kwargs["charset"] = charset

        return mysql_connector.connect(**connect_kwargs)

    def _create_cursor(self) -> Any:
        """Create dictionary-row cursors for readable DB assertions."""
        return self._conn.cursor(dictionary=True)