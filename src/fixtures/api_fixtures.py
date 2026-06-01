"""
API session fixtures — provide a configured APISession to tests.
"""
from __future__ import annotations

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
        api_cfg = config.get_api_config(config_section)
        session = APISession.from_config(api_cfg)
        yield session
        session.close()

    _api_fixture.__name__ = f"api_{config_section}"
    return _api_fixture
