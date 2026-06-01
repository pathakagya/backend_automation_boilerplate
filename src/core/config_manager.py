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
    api_timeout: int = Field(default=30, alias="API_TIMEOUT")
    api_verify_ssl: bool = Field(default=True, alias="API_VERIFY_SSL")
    api_proxy_url: str | None = Field(default=None, alias="API_PROXY_URL")
    api_max_retries: int = Field(default=2, alias="API_MAX_RETRIES")
    api_retry_backoff: float = Field(default=0.3, alias="API_RETRY_BACKOFF")

    # DB
    db_engine: str | None = Field(default=None, alias="DB_ENGINE")
    database_host: str | None = Field(default=None, alias="DATABASE_HOST")
    database_port: int | None = Field(default=None, alias="DATABASE_PORT")
    database_name: str | None = Field(default=None, alias="DATABASE_NAME")
    database_user: str | None = Field(default=None, alias="DATABASE_USER")
    database_password: str | None = Field(default=None, alias="DATABASE_PASSWORD")
    database_connect_timeout: int = Field(default=10, alias="DATABASE_CONNECT_TIMEOUT")
    database_ssl_disabled: bool | None = Field(default=None, alias="DATABASE_SSL_DISABLED")
    database_charset: str | None = Field(default=None, alias="DATABASE_CHARSET")


class ConfigManager:
    """Thin facade over environment-based settings with section-style accessors."""

    _ROOT = Path(__file__).resolve().parents[2]

    def __init__(self, env_file: str | None = None) -> None:
        selected_env = os.getenv("ENV", "qa").strip() or "qa"
        default_env_file = self._ROOT / "config" / ".env"
        scoped_env_file = self._ROOT / "config" / f".env.{selected_env}"
        chosen_env_file = Path(env_file) if env_file else (scoped_env_file if scoped_env_file.exists() else default_env_file)

        self._settings = _Settings(_env_file=chosen_env_file if chosen_env_file.exists() else None) # type: ignore
        self.environment = selected_env
        self.env_file = str(chosen_env_file)

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        env_key = f"{section.upper()}_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val

        section_data = self.get_section(section)
        return section_data.get(key.lower(), fallback)

    def require(self, section: str, key: str) -> Any:
        value = self.get(section, key)
        if value is None:
            raise ConfigError(f"Required config missing: {section}.{key} ({section.upper()}_{key.upper()})")
        return value

    def get_section(self, section: str) -> dict[str, Any]:
        section_name = section.lower()
        if section_name == "api":
            return self.get_api_config()
        if section_name == "database":
            return self.get_database_config()
        return {}

    def get_database_config(self, section: str = "database") -> dict[str, Any]:
        return {
            "engine": self._settings.db_engine,
            "host": self._settings.database_host,
            "port": self._settings.database_port,
            "name": self._settings.database_name,
            "user": self._settings.database_user,
            "password": self._settings.database_password,
            "connect_timeout": self._settings.database_connect_timeout,
            "ssl_disabled": self._settings.database_ssl_disabled,
            "charset": self._settings.database_charset,
        }

    def get_api_config(self, section: str = "api") -> dict[str, Any]:
        return {
            "base_url": self._settings.api_base_url,
            "auth_type": self._settings.api_auth_type,
            "token": self._settings.api_token,
            "username": self._settings.api_username,
            "password": self._settings.api_password,
            "timeout": self._settings.api_timeout,
            "verify_ssl": self._settings.api_verify_ssl,
            "proxy_url": self._settings.api_proxy_url,
            "max_retries": self._settings.api_max_retries,
            "retry_backoff": self._settings.api_retry_backoff,
        }

    def __repr__(self) -> str:
        return f"ConfigManager(env={self.environment!r})"
