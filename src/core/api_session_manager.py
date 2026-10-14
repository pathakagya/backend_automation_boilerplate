"""
APISessionManager: Generic HTTP session manager for API testing.

Wraps requests.Session with:
    - Auth handling (Bearer, Basic, API Key, Custom headers)
    - Base URL management
    - Configurable timeout
    - Automatic retries (optional)
    - Allure request/response attachment (optional)

Usage:
    cfg = {"base_url": "https://api.example.com", "auth_type": "bearer", "token": "abc123"}
    session = APISession.from_config(cfg)

"""
from __future__ import annotations

import json
from enum import Enum
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.shared_utils import get_allure_module, attach_json_to_allure, safe_json_serialize


class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api_key"
    API_KEY_PARAM = "api_key_param"
    CUSTOM_HEADERS = "custom_headers"


class APISessionError(Exception):
    """Raised when the API session cannot be configured."""


class APISession:
    """
    Generic requests-based HTTP session for API testing.

    Configuration dict keys (all optional unless noted):
        base_url            (str, required) — base URL for all requests
        auth_type           (str) — none, bearer, basic, api_key, api_key_param, or custom_headers
        token               (str) — used with auth_type=bearer
        username            (str) — used with auth_type=basic
        password            (str) — used with auth_type=basic
        api_key             (str) — used with auth_type=api_key / api_key_param
        api_key_header      (str) — header name for auth_type=api_key  (default: X-API-Key)
        api_key_param_name  (str) — query param name for auth_type=api_key_param  (default: api_key)
        custom_headers      (dict) — extra headers to add to all requests
        timeout             (int|float) — request timeout in seconds (default: 30)
        max_retries         (int) — number of retries on 5xx / connection errors (default: 0)
        retry_backoff       (float) — exponential backoff factor (default: 0.3)
        retry_unsafe_methods (bool) — allow retries for POST/PUT/PATCH/DELETE (default: false)
        attach_allure       (bool) — whether to attach request/response details to Allure reports (default: true)
    """

    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        base_url: str,
        auth_type: str = AuthType.NONE,
        *,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_header: str = "X-API-Key",
        api_key_param_name: str = "api_key",
        custom_headers: Optional[dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 0,
        retry_backoff: float = 0.3,
        retry_unsafe_methods: bool = False,
        attach_allure: bool = True,
    ) -> None:
        if not base_url:
            raise APISessionError("base_url is required")

        self.base_url = base_url.rstrip("/")
        self.auth_type = AuthType(auth_type.lower())
        self.timeout = float(timeout)
        self._session = requests.Session()
        self.attach_allure = attach_allure
        self._auth_query_params: dict[str, str] = {}

        # --- Auth configuration ---
        if self.auth_type == AuthType.BEARER:
            if not token:
                raise APISessionError("Authentication type 'bearer' requires a token")
            self._session.headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == AuthType.BASIC:
            if not (username and password):
                raise APISessionError("Authentication type 'basic' requires username and password")
            self._session.auth = (username, password)

        elif self.auth_type == AuthType.API_KEY:
            if not api_key:
                raise APISessionError("Authentication type 'api_key' requires api_key")
            self._session.headers[api_key_header] = api_key

        elif self.auth_type == AuthType.API_KEY_PARAM:
            if not api_key:
                raise APISessionError("Authentication type 'api_key_param' requires api_key")
            self._auth_query_params[api_key_param_name] = api_key

        elif self.auth_type == AuthType.CUSTOM_HEADERS:
            if custom_headers:
                self._session.headers.update(custom_headers)

        # Extra headers
        if custom_headers and self.auth_type != AuthType.CUSTOM_HEADERS:
            self._session.headers.update(custom_headers)

        # --- Retry adapter ---
        if max_retries > 0:
            retry = Retry(
                total=max_retries,
                backoff_factor=retry_backoff,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=(
                    ["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"]
                    if retry_unsafe_methods
                    else ["GET", "HEAD", "OPTIONS"]
                ),
            )
            adapter = HTTPAdapter(max_retries=retry)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

    # ------------------------------------------------------------------ #
    # HTTP methods( After instantiating API Session, use these methods to make requests. They mirror requests.Session methods but with base_url and auth handling.)
    # ------------------------------------------------------------------ #

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        """Send an authenticated GET request relative to the configured base URL."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        """Send an authenticated POST request relative to the configured base URL."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        """Send an authenticated PUT request relative to the configured base URL."""
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        """Send an authenticated PATCH request relative to the configured base URL."""
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        """Send an authenticated DELETE request relative to the configured base URL."""
        return self._request("DELETE", path, **kwargs)

    # ------------------------------------------------------------------ #
    # Core dispatcher
    # ------------------------------------------------------------------ #

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Dispatch one request, applying auth/query defaults and report attachments."""
        url = self.build_url(path)
        kwargs.setdefault("timeout", self.timeout)
        if self._auth_query_params:
            kwargs["params"] = {**self._auth_query_params, **(kwargs.get("params") or {})}

        if self.attach_allure:
            self._attach_request(method=method, url=url, kwargs=kwargs)
        response = self._session.request(method, url, **kwargs)
        if self.attach_allure:
            self._attach_response(method=method, url=url, response=response)
        return response

    def _attach_request(self, method: str, url: str, kwargs: dict[str, Any]) -> None:
        """Attach a sanitized outgoing request to the active Allure report."""
        payload = {
            "method": method,
            "url": url,
            "headers": self._sanitize(dict(self._session.headers)),
            "params": self._sanitize(kwargs.get("params")),
            "json": self._sanitize(kwargs.get("json")),
            "data": self._sanitize(kwargs.get("data")),
            "timeout": kwargs.get("timeout"),
        }
        attach_json_to_allure(payload, f"HTTP Request: {method} {url}")

    def _attach_response(self, method: str, url: str, response: requests.Response) -> None:
        """Attach sanitized response metadata and body to the active Allure report."""
        allure = get_allure_module()
        if allure is None:
            return

        try:
            body = self._sanitize(response.json())
            body_text = safe_json_serialize(body)
            atype = allure.attachment_type.JSON
        except Exception:
            body_text = response.text[:10000]
            atype = allure.attachment_type.TEXT

        metadata = {
            "method": method,
            "url": url,
            "status_code": response.status_code,
            "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
            "headers": self._sanitize(dict(response.headers)),
        }
        attach_json_to_allure(metadata, f"HTTP Response Meta: {method} {url}")
        allure.attach(body_text, name=f"HTTP Response Body: {method} {url}", attachment_type=atype)

    def build_url(self, path: str) -> str:
        """Resolve `path` to a full URL against base_url (or pass an absolute URL through)."""
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    @staticmethod
    def _sanitize(value: Any) -> Any:
        """Redact credentials and tokens before values are attached to Allure."""
        secret_names = ("authorization", "token", "password", "secret", "api-key", "apikey")
        if isinstance(value, dict):
            return {
                key: (
                    "<redacted>"
                    if any(name in str(key).lower() for name in secret_names)
                    else APISession._sanitize(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [APISession._sanitize(item) for item in value]
        return value

    # ------------------------------------------------------------------ #
    # Token refresh helper (extend for OAuth)
    # ------------------------------------------------------------------ #

    def set_bearer_token(self, token: str) -> None:
        """Update the Bearer token on the fly (e.g. after token refresh)."""
        self._session.headers["Authorization"] = f"Bearer {token}"

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Close the underlying requests.Session."""
        self._session.close()

    def __enter__(self) -> "APISession":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Factory
    # ------------------------------------------------------------------ #

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "APISession":
        """
        Build an APISession from a config dict (e.g. from ConfigManager.get_api_config()).

        Config keys map directly to __init__ parameters.
        """
        if "base_url" not in config:
            raise APISessionError(
                "base_url is required in API config.\n"
                "Set API_BASE_URL in your environment configuration."
            )

        # Map config keys → constructor kwargs
        kwargs: dict[str, Any] = {
            "base_url": config["base_url"],
            "auth_type": config.get("auth_type", AuthType.NONE),
            "token": config.get("token"),
            "username": config.get("username"),
            "password": config.get("password"),
            "api_key": config.get("api_key"),
            "api_key_header": config.get("api_key_header", "X-API-Key"),
            "api_key_param_name": config.get("api_key_param_name", "api_key"),
            "timeout": config.get("timeout", cls.DEFAULT_TIMEOUT),
            "max_retries": int(config.get("max_retries", 0)),
            "retry_backoff": float(config.get("retry_backoff", 0.3)),
            "retry_unsafe_methods": str(
                config.get("retry_unsafe_methods", False)
            ).lower() in ("true", "1", "yes"),
            "attach_allure": str(config.get("attach_allure", "true")).lower() not in ("false", "0", "no"),
        }

        # custom_headers: support both dict and comma-separated "Key:Value,Key2:Value2"
        custom_headers_raw = config.get("custom_headers")
        if isinstance(custom_headers_raw, dict):
            kwargs["custom_headers"] = custom_headers_raw
        elif isinstance(custom_headers_raw, str) and custom_headers_raw:
            headers = {}
            for pair in custom_headers_raw.split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    headers[k.strip()] = v.strip()
            kwargs["custom_headers"] = headers

        return cls(**{k: v for k, v in kwargs.items() if v is not None or k in ("auth_type",)})

    def __repr__(self) -> str:
        return f"APISession(base_url={self.base_url!r}, auth={self.auth_type.value!r})"
