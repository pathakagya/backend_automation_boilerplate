"""
Database fixtures — provide DB connections to tests.

These fixtures build on the generic DatabaseConnection base class.
Projects pass their own subclass implementation.

Setup in your project's conftest.py:
    from project.db import OracleConnection          # your subclass
    from fixtures.database_fixtures import make_db_fixture

    oracle = make_db_fixture(OracleConnection, config_section="oracle")

Or override db_connection directly:
    @pytest.fixture
    def db_connection(config):
        conn = OracleConnection.from_config(config.get_database_config("oracle"))
        conn.connect()
        yield conn
        conn.cleanup()   # auto-rollback + disconnect
"""
from __future__ import annotations

from typing import Callable, Generator, Type, Literal

import pytest

from core.config_manager import ConfigManager
from core.db_connection_manager import DatabaseConnection


# ---------------------------------------------------------------------------
# Generic DB fixture factory
# ---------------------------------------------------------------------------

def make_db_fixture(
    connection_class: Type[DatabaseConnection],
    config_section: str = "database",
    scope: Literal["function", "module", "session"] = "function",
) -> Callable:
    """
    Factory that creates a pytest fixture for a specific DatabaseConnection subclass.

    Args:
        connection_class: Your DatabaseConnection subclass.
        config_section:   Section name in config file (e.g. "oracle", "mssql").
        scope:            pytest scope — "function" (default), "module", "session".

    Returns:
        A pytest fixture function ready to be registered.

    Example:
        from myproject.connections import OracleConnection
        oracle_db = make_db_fixture(OracleConnection, config_section="oracle", scope="module")
        # Then in conftest.py: register it as a fixture with @pytest.fixture
    """
    @pytest.fixture(scope=scope)
    def _db_fixture(config: ConfigManager) -> Generator[DatabaseConnection, None, None]:
        """Create, yield, and clean up one explicitly configured DB adapter."""
        db_cfg = config.get_database_config(config_section)
        conn = connection_class.from_config(db_cfg)
        conn.connect()
        yield conn
        conn.cleanup()

    _db_fixture.__name__ = f"db_{config_section}"
    return _db_fixture
