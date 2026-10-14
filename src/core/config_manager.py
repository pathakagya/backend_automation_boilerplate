"""Environment-driven configuration based on Pydantic BaseSettings.

This intentionally keeps config simple and aligned with the framework plan:
    - Configuration is read from environment variables.
    - ENV selects the env file name (e.g. ENV=staging -> config/.env.staging).
    - config/.env is used as a default fallback if no ENV-specific file exists.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(Exception):
    """Raised when required configuration values are missing."""


class _Settings(BaseSettings):
    """Project settings loaded from env vars and optional .env file."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: str = Field(default="dev", alias="ENV")

    # API
    api_base_url: str | None = Field(default=None, alias="API_BASE_URL")
    api_auth_type: str = Field(default="none", alias="API_AUTH_TYPE")
    api_token: str | None = Field(default=None, alias="API_TOKEN")
    api_username: str | None = Field(default=None, alias="API_USERNAME")
    api_password: str | None = Field(default=None, alias="API_PASSWORD")
    api_key: str | None = Field(default=None, alias="API_KEY")
    api_key_header: str = Field(default="X-API-Key", alias="API_KEY_HEADER")
    api_key_param_name: str = Field(default="api_key", alias="API_KEY_PARAM_NAME")
    api_timeout: int = Field(default=30, alias="API_TIMEOUT")
    api_verify_ssl: bool = Field(default=True, alias="API_VERIFY_SSL")
    api_proxy_url: str | None = Field(default=None, alias="API_PROXY_URL")
    api_max_retries: int = Field(default=2, alias="API_MAX_RETRIES")
    api_retry_backoff: float = Field(default=0.3, alias="API_RETRY_BACKOFF")
    api_retry_unsafe_methods: bool = Field(default=False, alias="API_RETRY_UNSAFE_METHODS")

    # DB
    db_engine: str | None = Field(default=None, alias="DB_ENGINE")
    database_host: str | None = Field(default=None, alias="DATABASE_HOST")
    database_port: int | None = Field(default=None, alias="DATABASE_PORT")
    database_name: str | None = Field(default=None, alias="DATABASE_NAME")
    database_user: str | None = Field(default=None, alias="DATABASE_USER")
    database_password: str | None = Field(default=None, alias="DATABASE_PASSWORD")
    database_adapter_class: str | None = Field(default=None, alias="DB_ADAPTER_CLASS")
    database_connect_timeout: int = Field(default=10, alias="DATABASE_CONNECT_TIMEOUT")
    database_ssl_disabled: bool | None = Field(default=None, alias="DATABASE_SSL_DISABLED")
    database_charset: str | None = Field(default=None, alias="DATABASE_CHARSET")


class ConfigManager:
    """Thin facade over environment-based settings with section-style accessors."""

    _ROOT = Path(__file__).resolve().parents[2]

    def __init__(self, env_file: str | None = None) -> None:
        selected_env = os.getenv("ENV", "dev").strip() or "dev"
        default_env_file = self._ROOT / "config" / ".env"
        scoped_env_file = self._ROOT / "config" / f".env.{selected_env}"
        chosen_env_file = Path(env_file) if env_file else (scoped_env_file if scoped_env_file.exists() else default_env_file)

        if chosen_env_file.exists():
            # Only _Settings' declared fields (primary API_*/DATABASE_* vars) load from the file
            # otherwise. This makes secondary/named-section vars (e.g. BILLING_API_BASE_URL,
            # AUTH_SERVICE_BASE_URL) visible via os.environ too, without overriding shell exports.
            load_dotenv(chosen_env_file, override=False)

        self._settings = _Settings(_env_file=chosen_env_file if chosen_env_file.exists() else None) # type: ignore
        self.environment = selected_env
        self.env_file = str(chosen_env_file)

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Read a setting from process environment, loaded config, or fallback."""
        env_key = f"{section.upper()}_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val

        section_data = self.get_section(section)
        return section_data.get(key.lower(), fallback)

    def require(self, section: str, key: str) -> Any:
        """Return a required setting or raise ``ConfigError`` with its env name."""
        value = self.get(section, key)
        if value is None:
            raise ConfigError(f"Required config missing: {section}.{key} ({section.upper()}_{key.upper()})")
        return value

    def validate_api(self) -> None:
        """Validate that the primary API has a base URL and compatible auth data."""
        config = self.get_api_config()
        if not config.get("base_url"):
            raise ConfigError("API_BASE_URL is required to run API tests")
        auth_type = str(config.get("auth_type", "none")).lower()
        required = {
            "bearer": ("token",),
            "basic": ("username", "password"),
            "api_key": ("api_key",),
            "api_key_param": ("api_key",),
        }.get(auth_type, ())
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise ConfigError(
                f"API auth type {auth_type!r} is missing: {', '.join(missing)}"
            )

    def validate_database(self) -> None:
        """Validate DB settings before a DB-required command starts."""
        config = self.get_database_config()
        if not config.get("adapter_class") and not config.get("engine"):
            raise ConfigError(
                "DB_ADAPTER_CLASS is required for DB-backed tests "
                "(DB_ENGINE=mysql is retained for the reference adapter)"
            )
        required = ("host", "port", "name", "user", "password")
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise ConfigError(
                f"Database configuration is missing: {', '.join(missing)}"
            )

    def get_section(self, section: str) -> dict[str, Any]:
        """Return a named configuration section as a plain dictionary."""
        section_name = section.lower()
        if section_name == "api":
            return self.get_api_config()
        if section_name == "database":
            return self.get_database_config()
        return {}

    def get_database_config(self, section: str = "database") -> dict[str, Any]:
        """
        Build a DatabaseConnection.from_config()-compatible dict.

        section="database" (default) returns the primary DATABASE_*/DB_ENGINE settings. Any
        other section name (e.g. "oracle") reads {SECTION}_HOST, {SECTION}_PORT, etc. directly
        from the environment — see make_db_fixture() in src/fixtures/database_fixtures.py.
        """
        if section.lower() == "database":
            return {
                "engine": self._settings.db_engine,
                "host": self._settings.database_host,
                "port": self._settings.database_port,
                "name": self._settings.database_name,
                "user": self._settings.database_user,
                "password": self._settings.database_password,
                "adapter_class": self._settings.database_adapter_class,
                "connect_timeout": self._settings.database_connect_timeout,
                "ssl_disabled": self._settings.database_ssl_disabled,
                "charset": self._settings.database_charset,
            }

        prefix = section.upper()
        return {
            "engine": os.environ.get(f"{prefix}_ENGINE"),
            "host": os.environ.get(f"{prefix}_HOST"),
            "port": os.environ.get(f"{prefix}_PORT"),
            "name": os.environ.get(f"{prefix}_NAME"),
            "user": os.environ.get(f"{prefix}_USER"),
            "password": os.environ.get(f"{prefix}_PASSWORD"),
            "connect_timeout": int(
                os.environ.get(f"{prefix}_CONNECT_TIMEOUT", self._settings.database_connect_timeout)
            ),
            "ssl_disabled": os.environ.get(f"{prefix}_SSL_DISABLED"),
            "charset": os.environ.get(f"{prefix}_CHARSET"),
        }

    def get_api_config(self, section: str = "api") -> dict[str, Any]:
        """
        Build an APISession.from_config()-compatible dict.

        section="api" (default) returns the primary API_* settings. Any other section name
        (e.g. "billing_api") reads {SECTION}_BASE_URL, {SECTION}_AUTH_TYPE, etc. directly from
        the environment — see make_api_fixture() in src/fixtures/api_fixtures.py.
        """
        if section.lower() == "api":
            return {
                "base_url": self._settings.api_base_url,
                "auth_type": self._settings.api_auth_type,
                "token": self._settings.api_token,
                "username": self._settings.api_username,
                "password": self._settings.api_password,
                "api_key": self._settings.api_key,
                "api_key_header": self._settings.api_key_header,
                "api_key_param_name": self._settings.api_key_param_name,
                "timeout": self._settings.api_timeout,
                "verify_ssl": self._settings.api_verify_ssl,
                "proxy_url": self._settings.api_proxy_url,
                "max_retries": self._settings.api_max_retries,
                "retry_backoff": self._settings.api_retry_backoff,
                "retry_unsafe_methods": self._settings.api_retry_unsafe_methods,
            }

        prefix = section.upper()
        return {
            "base_url": os.environ.get(f"{prefix}_BASE_URL"),
            "auth_type": os.environ.get(f"{prefix}_AUTH_TYPE", "none"),
            "token": os.environ.get(f"{prefix}_TOKEN"),
            "username": os.environ.get(f"{prefix}_USERNAME"),
            "password": os.environ.get(f"{prefix}_PASSWORD"),
            "api_key": os.environ.get(f"{prefix}_API_KEY"),
            "api_key_header": os.environ.get(f"{prefix}_API_KEY_HEADER", "X-API-Key"),
            "timeout": float(os.environ.get(f"{prefix}_TIMEOUT", self._settings.api_timeout)),
            "max_retries": int(os.environ.get(f"{prefix}_MAX_RETRIES", 0)),
            "retry_backoff": float(os.environ.get(f"{prefix}_RETRY_BACKOFF", 0.3)),
        }

    def __repr__(self) -> str:
        return f"ConfigManager(env={self.environment!r})"
