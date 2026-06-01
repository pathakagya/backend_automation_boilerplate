"""
Smoke tests — quick sanity checks (health, connectivity).
Run these first before the full suite.
"""
import os
import allure
import pytest

from core.constants import APIPath, SmokeDefaults, SmokeModule
from helpers.assertions import assert_response_status, assert_response_time


def _parse_csv_env(env_key: str, default_values: tuple[str, ...] = ()) -> list[str]:
    raw = os.getenv(env_key)
    if raw is None:
        return list(default_values)
    values = [value.strip() for value in raw.split(",")]
    return [value for value in values if value]


def _resolve_required_value(config, env_key: str) -> str | None:
    direct = os.getenv(env_key)
    if direct:
        return direct

    if env_key == "ENV":
        return getattr(config, "environment", None)

    if "_" not in env_key:
        return None

    section, key = env_key.split("_", 1)
    value = config.get(section, key.lower())
    return value if isinstance(value, str) and value else None


def _discover_get_endpoints(api_session) -> list[str]:
    openapi_path = os.getenv("SMOKE_OPENAPI_PATH", SmokeDefaults.OPENAPI_PATH)
    response = api_session.get(openapi_path)
    if response.status_code != 200:
        return []

    try:
        payload = response.json()
    except Exception:
        return []

    paths = payload.get("paths", {})
    if not isinstance(paths, dict):
        return []

    endpoints: list[str] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        has_get = any(str(method).lower() == "get" for method in methods.keys())
        if has_get and "{" not in path and "}" not in path:
            endpoints.append(path)
    return sorted(set(endpoints))


def _default_get_endpoints() -> list[str]:
    endpoints = []
    for value in vars(APIPath).values():
        if isinstance(value, str) and value.startswith("/"):
            endpoints.append(value)
    return sorted(set(endpoints))


def _health_target(api_session, endpoint: str) -> str:
    if endpoint.startswith(("http://", "https://")):
        return endpoint

    explicit_base = os.getenv("SMOKE_HEALTH_BASE_URL", "").strip().rstrip("/")
    if explicit_base:
        return f"{explicit_base}/{endpoint.lstrip('/')}"

    api_base = getattr(api_session, "base_url", "").rstrip("/")
    if api_base.endswith("/api"):
        root_base = api_base[: -len("/api")]
        return f"{root_base}/{endpoint.lstrip('/')}"

    return endpoint


def _root_fallback_target(api_session, endpoint: str) -> str | None:
    if endpoint.startswith(("http://", "https://")):
        return None

    api_base = getattr(api_session, "base_url", "").rstrip("/")
    if api_base.endswith("/api"):
        root_base = api_base[: -len("/api")]
        return f"{root_base}/{endpoint.lstrip('/')}"
    return None


@allure.feature("Smoke")
@pytest.mark.smoke
class TestSmoke:

    @allure.title("Health check endpoints are reachable")
    def test_health_check_endpoints(self, api_session):
        endpoints = _parse_csv_env("SMOKE_HEALTH_ENDPOINTS", SmokeDefaults.HEALTH_ENDPOINTS)

        for endpoint in endpoints:
            target = _health_target(api_session, endpoint)
            with allure.step(f"GET {target}"):
                response = api_session.get(target)
            with allure.step("Assert response status and time"):
                assert_response_status(response, SmokeModule.HEALTH)
                assert_response_time(response, SmokeModule.HEALTH)

    @allure.title("Database connectivity check")
    def test_database_connectivity(self, db_connection):
        with allure.step("Run DB query"):
            row = db_connection.fetch_one("SELECT 1 AS ok")

        value = row.get("ok") if isinstance(row, dict) else None
        assert value == 1, f"Expected DB heartbeat value 1, got {value!r}"

    @allure.title("Application config loads without error")
    def test_application_starts_and_config_loads(self, config):
        with allure.step("Read API and DB configuration"):
            api_cfg = config.get_api_config()
            db_cfg = config.get_database_config()

        assert isinstance(api_cfg, dict), "API config must be a dictionary"
        assert isinstance(db_cfg, dict), "DB config must be a dictionary"
        assert config.environment, "Config environment should not be empty"

    @allure.title("Required environment variables and secrets are accessible")
    def test_required_environment_variables_are_accessible(self, config):
        required_env_vars = _parse_csv_env("SMOKE_REQUIRED_ENV_VARS", SmokeDefaults.REQUIRED_ENV_VARS)
        required_secret_vars = _parse_csv_env("SMOKE_REQUIRED_SECRET_VARS", SmokeDefaults.REQUIRED_SECRET_VARS)

        missing_env = [key for key in required_env_vars if not _resolve_required_value(config, key)]
        missing_secrets = [key for key in required_secret_vars if not _resolve_required_value(config, key)]

        assert not missing_env, f"Missing required environment variables: {', '.join(missing_env)}"
        assert not missing_secrets, f"Missing required secret variables: {', '.join(missing_secrets)}"

    @allure.title("Configured GET endpoints are reachable")
    def test_all_get_endpoints(self, api_session):
        endpoints = _parse_csv_env("SMOKE_GET_ENDPOINTS", tuple(_default_get_endpoints()))
        if not endpoints:
            endpoints = _discover_get_endpoints(api_session)

        if not endpoints:
            pytest.skip(
                "No GET endpoints configured. Set SMOKE_GET_ENDPOINTS or expose OpenAPI at SMOKE_OPENAPI_PATH."
            )

        for endpoint in endpoints:
            with allure.step(f"GET {endpoint}"):
                response = api_session.get(endpoint)
                if response.status_code == 404:
                    fallback_target = _root_fallback_target(api_session, endpoint)
                    if fallback_target:
                        response = api_session.get(fallback_target)
            assert_response_status(response, SmokeModule.GENERIC_GET)
            assert_response_time(response, SmokeModule.GENERIC_GET)

    @allure.title("Database master tables are accessible")
    def test_database_master_tables_accessible(self, db_connection):
        master_tables = _parse_csv_env("SMOKE_DB_MASTER_TABLES", SmokeDefaults.DB_MASTER_TABLES)
        for table in master_tables:
            with allure.step(f"Query master table {table}"):
                row = db_connection.fetch_one(f"SELECT 1 AS ok FROM {table} LIMIT 1")
            value = row.get("ok") if isinstance(row, dict) else None
            assert value == 1, f"Expected to access master table {table}, got {value!r}"