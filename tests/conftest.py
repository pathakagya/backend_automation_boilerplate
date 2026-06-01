"""
tests/conftest.py — project-level fixtures.

Keep this file generic and lightweight:
- reuse one API session for the test session
- optionally create dedicated service sessions from env base URLs
- reuse one DB connection for the test session

Project-specific flows, ordering, metadata, or service auth logic should live in
project-specific test packages, not here.
"""
from __future__ import annotations

import importlib
import os

import pytest
from typing import Generator
from core.api_session_manager import APISession
from core.constants import Timeout
from core.db_connection_manager import DatabaseConnection


class SharedTestResources:
    """Centralized API/DB bootstrap used across tests."""

    def __init__(self) -> None:
        self._api_sessions: dict[str, APISession] = {}
        self._db_connection: DatabaseConnection | None = None

    def get_primary_api_session(self, config) -> APISession:
        key = "primary"
        if key not in self._api_sessions:
            self._api_sessions[key] = APISession.from_config(config.get_api_config())
        return self._api_sessions[key]

    def get_service_api_session(self, service_name: str, base_url: str | None, config) -> APISession:
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

    def get_db_connection(self, config) -> DatabaseConnection:
        if self._db_connection is not None:
            return self._db_connection

        db_cfg = config.get_database_config()
        engine = (db_cfg.get("engine") or "mysql").lower()
        
        # Map database engines to their connection class modules and names
        engine_map = {
            "mysql": ("project.db.mysql_connection", "MySQLConnection"),
            "postgresql": ("project.db.postgresql_connection", "PostgreSQLConnection"),
            "postgres": ("project.db.postgresql_connection", "PostgreSQLConnection"),  # alias
            "oracle": ("project.db.oracle_connection", "OracleConnection"),
        }
        
        if engine not in engine_map:
            supported = ", ".join(engine_map.keys())
            pytest.skip(f"Unsupported DB engine: {engine!r}. Supported: {supported}")
        
        # Validate required configuration keys
        required = ("host", "port", "name", "user", "password")
        missing = [key for key in required if not db_cfg.get(key)]
        if missing:
            pytest.skip(f"Database config incomplete for {engine}. Missing: {', '.join(missing)}")
        
        # Dynamically import the appropriate connection class
        module_name, class_name = engine_map[engine]
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

    def close(self) -> None:
        if self._db_connection is not None:
            self._db_connection.cleanup()
            self._db_connection = None

        for session in self._api_sessions.values():
            session.close()
        self._api_sessions.clear()


@pytest.fixture(scope="session")
def shared_test_resources() -> Generator[SharedTestResources, None, None]:
    resources = SharedTestResources()
    yield resources
    resources.close()


@pytest.fixture(scope="session")
def api_session(config, shared_test_resources: SharedTestResources) -> APISession:
    return shared_test_resources.get_primary_api_session(config)


@pytest.fixture(scope="session")
def auth_service_session(config, shared_test_resources: SharedTestResources) -> APISession:
    base_url = os.getenv("AUTH_SERVICE_BASE_URL", "").strip() or None
    return shared_test_resources.get_service_api_session("auth", base_url, config)


@pytest.fixture(scope="session")
def db_connection(config, shared_test_resources: SharedTestResources) -> DatabaseConnection:
    return shared_test_resources.get_db_connection(config)
