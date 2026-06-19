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

import os
from typing import Generator

import pytest

from core.api_session_manager import APISession
from core.db_connection_manager import DatabaseConnection
from core.test_resources import TestResourcesManager


@pytest.fixture(scope="session")
def shared_test_resources() -> Generator[TestResourcesManager, None, None]:
    """Session-scoped resource manager for API sessions and database connections."""
    resources = TestResourcesManager()
    yield resources
    resources.cleanup()


@pytest.fixture(scope="session")
def api_session(config, shared_test_resources: TestResourcesManager) -> APISession:
    """Primary API session used across tests."""
    return shared_test_resources.get_primary_api_session(config)


@pytest.fixture(scope="session")
def auth_service_session(
    config,
    shared_test_resources: TestResourcesManager,
) -> APISession:
    """Optional secondary API session for authentication service."""
    base_url = os.getenv("AUTH_SERVICE_BASE_URL", "").strip() or None
    return shared_test_resources.get_service_api_session("auth", base_url, config)


@pytest.fixture(scope="session")
def db_connection(
    config,
    shared_test_resources: TestResourcesManager,
) -> DatabaseConnection:
    """Database connection used across tests."""
    return shared_test_resources.get_db_connection(config)
