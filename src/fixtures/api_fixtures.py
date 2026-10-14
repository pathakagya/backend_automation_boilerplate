"""
API session fixtures — provide a configured APISession to tests.
"""
from __future__ import annotations

import os
from typing import Generator, Literal

import pytest

from core.api_session_manager import APISession
from core.auth_client import AuthClient
from core.config_manager import ConfigManager


@pytest.fixture
def api_session(config: ConfigManager) -> Generator[APISession, None, None]:
    """
    Function-scoped API session fixture.

    Reads configuration from the [api] section of your config file.
    All requests made through this session share the configured:
        - base_url
        - auth headers / credentials
        - timeout and SSL settings

    Usage:
        def test_get_user(api_session):
            resp = api_session.get("/users/1")
            assert resp.status_code == 200

    Override in your project's conftest.py to use a different config section:
        @pytest.fixture
        def api_session(config):
            session = APISession.from_config(config.get_api_config("my_service"))
            yield session
            session.close()
    """
    api_cfg = config.get_api_config()
    session = APISession.from_config(api_cfg)
    yield session
    session.close()


@pytest.fixture(scope="session")
def auth_client(config: ConfigManager) -> Generator[AuthClient, None, None]:
    """Centralized auth client used for token retrieval and refresh workflows."""
    session = APISession.from_config(config.get_api_config())
    client = AuthClient(session=session)
    yield client
    session.close()


@pytest.fixture
def role_api_session(config: ConfigManager, auth_client: AuthClient) -> Generator[APISession, None, None]:
    """Pre-authenticated API session for role-based test scenarios."""
    api_cfg = config.get_api_config()
    session = APISession.from_config(api_cfg)

    role_username = config.get("api", "role_username")
    role_password = config.get("api", "role_password")
    if role_username and role_password:
        token = auth_client.get_valid_token(username=role_username, password=role_password)
        session.set_bearer_token(token)

    yield session
    session.close()


def make_role_fixture(
    role_name: str,
    scope: Literal["function", "class", "module", "session"] = "function",
    login_path: str = "/auth/token",
    token_key: str = "access_token",
):
    """
    Factory for a per-role authenticated APISession.

    Reads {ROLE}_API_USERNAME and {ROLE}_API_PASSWORD from the environment
    (role_name="admin" → section="admin_api" → ADMIN_API_USERNAME / ADMIN_API_PASSWORD).
    Uses the primary API base_url; authenticates via AUTH_SERVICE_BASE_URL if set.
    Skips the test gracefully when credentials are not configured.

    Usage in tests/conftest.py (or a module conftest):
        from fixtures.api_fixtures import make_role_fixture
        admin_session = make_role_fixture("admin")
        viewer_session = make_role_fixture("viewer")
    """
    section = f"{role_name}_api"

    @pytest.fixture(scope=scope, name=f"{role_name}_session")
    def _fixture(config: ConfigManager) -> Generator[APISession, None, None]:
        username = config.get(section, "username")
        password = config.get(section, "password")
        if not username or not password:
            pytest.skip(
                f"Role '{role_name}' credentials not configured: "
                f"{section.upper()}_USERNAME / {section.upper()}_PASSWORD"
            )
        api_cfg = config.get_api_config()
        session = APISession(
            base_url=api_cfg["base_url"],
            auth_type="bearer",
            timeout=api_cfg.get("timeout", 30),
        )
        auth_base = os.getenv("AUTH_SERVICE_BASE_URL", "").strip() or api_cfg["base_url"]
        auth_session = APISession(base_url=auth_base)
        auth_client = AuthClient(auth_session, login_path=login_path, token_key=token_key)
        session.set_bearer_token(auth_client.authenticate(username, password))
        yield session
        session.close()
        auth_session.close()

    return _fixture


def make_api_fixture(config_section: str = "api", scope: Literal["function", "class", "module", "package", "session"] = "function"):
    """
    Factory for creating API session fixtures targeting a specific config section.

    Example — multiple services:
        # tests/conftest.py
        from fixtures.api_fixtures import make_api_fixture

        notifications_session = make_api_fixture("notifications_api")
    """
    @pytest.fixture(scope=scope)
    def _api_fixture(config: ConfigManager) -> Generator[APISession, None, None]:
        """Create, yield, and close one configured service API session."""
        api_cfg = config.get_api_config(config_section)
        session = APISession.from_config(api_cfg)
        yield session
        session.close()

    _api_fixture.__name__ = f"api_{config_section}"
    return _api_fixture
