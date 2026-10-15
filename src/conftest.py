"""
Root conftest.py — session-scoped fixtures shared across ALL tests.

Fixture hierarchy:
    conftest.py (this file)  ← session scope: config
    └── tests/conftest.py    ← module/function scope: db connections, api sessions
        ├── tests/integration/conftest.py
        └── tests/e2e/conftest.py

Adding project-specific fixtures:
    Create tests/<feature>/conftest.py and import/override fixtures as needed.
    Do NOT modify this file for project-specific setup.
"""
import os
import uuid
from pathlib import Path
from shutil import copyfile
from typing import Generator

import pytest

from core.config_manager import ConfigManager
from core.state_manager import StateManager

# ---------------------------------------------------------------------------
# Pytest hooks
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers so pytest doesn't warn about unknown ones."""
    config.addinivalue_line("markers", "integration: tests requiring DB or API connectivity")
    config.addinivalue_line("markers", "e2e: end-to-end multi-step workflow tests")
    config.addinivalue_line("markers", "smoke: subset of critical-path tests")
    config.addinivalue_line(
        "markers", "db_required: tests requiring a project-owned database adapter"
    )
    config.addinivalue_line(
        "markers",
        "rbac: tests that exercise role-based access control; skipped when role credentials are not configured",
    )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _resolve_config_manager() -> ConfigManager:
    """Create the shared configuration facade for the current environment."""
    return ConfigManager()


@pytest.fixture(scope="session")
def config() -> ConfigManager:
    """
    Session-scoped configuration manager.

    Usage in tests or child conftest files:
        def test_something(config):
            url = config.require("api", "base_url")
            db_cfg = config.get_database_config()
    """
    return _resolve_config_manager()


@pytest.fixture(scope="session")
def run_prefix() -> str:
    """Run-scoped unique prefix used to isolate test data across parallel workers."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    return f"run_{worker_id}_{uuid.uuid4().hex[:8]}"


def pytest_sessionstart(session: pytest.Session) -> None:
    """Write Allure metadata files used by report UI."""
    root = Path(__file__).resolve().parent.parent
    allure_results = root / "allure-results"
    allure_results.mkdir(parents=True, exist_ok=True)

    env_lines = [
        f"API_URL={os.getenv('API_BASE_URL', '')}",
        f"DB_ENGINE={os.getenv('DB_ENGINE', '')}",
        f"BRANCH={os.getenv('GITHUB_REF_NAME', '')}",
        f"BUILD_NUMBER={os.getenv('GITHUB_RUN_NUMBER', '')}",
        f"ENV={os.getenv('ENV', 'dev')}",
    ]
    (allure_results / "environment.properties").write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    categories_src = root / "config" / "allure_categories.json"
    if categories_src.exists():
        copyfile(categories_src, allure_results / "categories.json")


# ---------------------------------------------------------------------------
# State manager (one per test function)
# ---------------------------------------------------------------------------

@pytest.fixture
def state() -> Generator[StateManager, None, None]:
    """
    Function-scoped test state store for multi-step workflows.

    Usage:
        def test_workflow(state, api_session):
            resp = api_session.post("/users", json={...})
            state.set("user_id", resp.json()["id"])

    The state is automatically cleared after each test.
    """
    sm = StateManager()
    yield sm
    sm.clear()
