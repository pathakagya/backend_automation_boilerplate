"""
Test resources manager — centralized session-scoped resource lifecycle management.

Handles API sessions and database connections with proper caching and cleanup.
Extracted from tests/conftest.py to avoid duplication and improve reusability.
"""
from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING

import pytest

from core.api_session_manager import APISession
from core.constants import Timeout
from core.db_connection_manager import DatabaseConnection

if TYPE_CHECKING:
    from core.config_manager import ConfigManager


class TestResourcesManager:
    """
    Centralized manager for session-scoped test resources.

    Handles caching and lifecycle management of:
    - Primary API session
    - Secondary/service API sessions
    - Database connection

    Usage:
        resources = TestResourcesManager()
        api_session = resources.get_primary_api_session(config)
        db_conn = resources.get_db_connection(config)
        resources.cleanup()  # in fixture teardown
    """

    # Supported database engines and their module/class locations
    DB_ENGINE_MAP = {
        "mysql": ("project.db.mysql_connection", "MySQLConnection"),
        "postgresql": ("project.db.postgresql_connection", "PostgreSQLConnection"),
        "postgres": ("project.db.postgresql_connection", "PostgreSQLConnection"),  # alias
        "oracle": ("project.db.oracle_connection", "OracleConnection"),
    }

    def __init__(self) -> None:
        self._api_sessions: dict[str, APISession] = {}
        self._db_connection: DatabaseConnection | None = None

    def get_primary_api_session(self, config: ConfigManager) -> APISession:
        """
        Get or create the primary API session.

        Cached and reused across tests within the session scope.

        Args:
            config: ConfigManager instance.

        Returns:
            Configured APISession for the primary API.
        """
        key = "primary"
        if key not in self._api_sessions:
            api_cfg = config.get_api_config()
            self._api_sessions[key] = APISession.from_config(api_cfg)
        return self._api_sessions[key]

    def get_service_api_session(
        self,
        service_name: str,
        base_url: str | None,
        config: ConfigManager,
    ) -> APISession:
        """
        Get or create a secondary/service API session.

        Useful for multi-service test scenarios (e.g., auth service, notifications).
        Falls back to primary session if base_url is None.

        Args:
            service_name: Descriptive name for the service (e.g., "auth", "notifications").
            base_url: Base URL for the service. If None, returns primary session.
            config: ConfigManager instance.

        Returns:
            Configured APISession for the service.
        """
        if not base_url:
            return self.get_primary_api_session(config)

        key = f"service:{service_name}:{base_url.rstrip('/')}"
        if key not in self._api_sessions:
            self._api_sessions[key] = APISession(
                base_url=base_url,
                auth_type="none",
                timeout=Timeout.DEFAULT,
                attach_allure=True,
            )
        return self._api_sessions[key]

    def get_db_connection(self, config: ConfigManager) -> DatabaseConnection:
        """
        Get or create the database connection.

        Cached and reused across tests within the session scope.
        Dynamically loads the appropriate driver based on DB_ENGINE config.

        Args:
            config: ConfigManager instance.

        Returns:
            Connected DatabaseConnection instance.

        Raises:
            pytest.skip: If engine is unsupported, config is incomplete, or driver load fails.
        """
        if self._db_connection is not None:
            return self._db_connection

        db_cfg = config.get_database_config()
        engine = (db_cfg.get("engine") or "mysql").lower()

        # Validate engine is supported
        if engine not in self.DB_ENGINE_MAP:
            supported = ", ".join(self.DB_ENGINE_MAP.keys())
            pytest.skip(
                f"Unsupported DB engine: {engine!r}. Supported: {supported}"
            )

        # Validate required config keys
        required = ("host", "port", "name", "user", "password")
        missing = [key for key in required if not db_cfg.get(key)]
        if missing:
            pytest.skip(
                f"Database config incomplete for {engine}. Missing: {', '.join(missing)}"
            )

        # Dynamically import and instantiate the connection class
        module_name, class_name = self.DB_ENGINE_MAP[engine]
        try:
            module = importlib.import_module(module_name)
            connection_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            pytest.skip(f"Cannot load {class_name} from {module_name}: {e}")

        # Create and connect
        conn = connection_class.from_config(db_cfg)
        conn.connect()
        self._db_connection = conn
        return conn

    def cleanup(self) -> None:
        """
        Clean up all cached resources.

        Disconnects database and closes all API sessions.
        Called in fixture teardown.
        """
        if self._db_connection is not None:
            self._db_connection.cleanup()
            self._db_connection = None

        for session in self._api_sessions.values():
            session.close()
        self._api_sessions.clear()
