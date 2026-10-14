"""
Test resources manager — centralized session-scoped resource lifecycle management.

Handles API sessions and database connections with proper caching and cleanup.
Extracted from tests/conftest.py to avoid duplication and improve reusability.
"""
from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING

from core.api_session_manager import APISession
from core.constants import Timeout
from core.db_connection_manager import DatabaseConnection
from core.db_adapter import DatabaseAdapterUnavailable

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

    # The shared core only includes the reference MySQL adapter. Other
    # projects register their own adapter with DB_ADAPTER_CLASS.
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
        Loads DB_ADAPTER_CLASS when supplied. DB_ENGINE remains a compatibility
        shortcut for the reference MySQL example only.

        Args:
            config: ConfigManager instance.

        Returns:
            Connected DatabaseConnection instance.

        Raises:
            DatabaseAdapterUnavailable: If the project adapter/configuration
                cannot be resolved.
        """
        if self._db_connection is not None:
            return self._db_connection

        db_cfg = config.get_database_config()
        adapter_path = db_cfg.get("adapter_class") or os.getenv("DB_ADAPTER_CLASS")
        engine = (db_cfg.get("engine") or "").lower()

        if not adapter_path and engine not in self.DB_ENGINE_MAP:
            supported = ", ".join(self.DB_ENGINE_MAP.keys())
            raise DatabaseAdapterUnavailable(
                "No project DB adapter is configured. Set DB_ADAPTER_CLASS to "
                "an importable adapter class. The reference engine aliases are: "
                f"{supported}."
            )

        # Validate required config keys
        required = ("host", "port", "name", "user", "password")
        missing = [key for key in required if not db_cfg.get(key)]
        if missing:
            raise DatabaseAdapterUnavailable(
                f"Database configuration is incomplete for {engine or 'configured adapter'}. "
                f"Missing: {', '.join(missing)}."
            )

        # Dynamically import and instantiate the connection class
        if adapter_path:
            module_name, class_name = adapter_path.rsplit(":", 1)
        else:
            module_name, class_name = self.DB_ENGINE_MAP[engine]
        try:
            module = importlib.import_module(module_name)
            connection_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise DatabaseAdapterUnavailable(
                f"Cannot load DB adapter {adapter_path or f'{module_name}:{class_name}'}. "
                "Install the project-owned driver and verify DB_ADAPTER_CLASS."
            ) from e

        # Create and connect
        try:
            conn = connection_class.from_config(db_cfg)
            conn.connect()
        except Exception as exc:
            raise DatabaseAdapterUnavailable(
                f"DB adapter {adapter_path or f'{module_name}:{class_name}'} "
                f"could not connect: {exc}"
            ) from exc
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
