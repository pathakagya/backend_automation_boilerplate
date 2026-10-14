"""Centralized authentication client with token caching and refresh support."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from core.api_session_manager import APISession


@dataclass
class TokenInfo:
    access_token: str
    expires_at_epoch: float


class AuthClient:
    """Handles token retrieval, caching, and refresh for API tests."""

    def __init__(
        self,
        session: APISession,
        login_path: str = "/auth/token",
        refresh_path: str = "/auth/refresh",
        token_key: str = "access_token",
        expires_in_key: str = "expires_in",
        refresh_token_key: str = "refresh_token",
    ) -> None:
        self.session = session
        self.login_path = login_path
        self.refresh_path = refresh_path
        self.token_key = token_key
        self.expires_in_key = expires_in_key
        self.refresh_token_key = refresh_token_key
        self._token: TokenInfo | None = None
        self._refresh_token: str | None = None

    def authenticate(self, username: str, password: str) -> str:
        """Authenticate once, cache the token, and update the API session."""
        response = self.session.post(self.login_path, json={"username": username, "password": password})
        response.raise_for_status()
        payload = response.json()

        token = str(payload[self.token_key])
        expires_in = int(payload.get(self.expires_in_key, 1800))
        self._token = TokenInfo(access_token=token, expires_at_epoch=time.time() + expires_in - 30)
        self._refresh_token = payload.get(self.refresh_token_key)
        self.session.set_bearer_token(token)
        return token

    def get_valid_token(self, username: str | None = None, password: str | None = None) -> str:
        """Return a cached, refreshed, or newly authenticated access token."""
        if self._token and self._token.expires_at_epoch > time.time():
            return self._token.access_token

        if self._refresh_token:
            token = self._refresh()
            if token:
                return token

        if username and password:
            return self.authenticate(username, password)

        raise ValueError("No valid token in cache and no credentials were provided for re-authentication.")

    def _refresh(self) -> str | None:
        """Try to refresh the cached token; return ``None`` on refresh failure."""
        import warnings
        try:
            response = self.session.post(self.refresh_path, json={self.refresh_token_key: self._refresh_token})
            response.raise_for_status()
            payload = response.json()
            token = str(payload[self.token_key])
            expires_in = int(payload.get(self.expires_in_key, 1800))
            self._token = TokenInfo(access_token=token, expires_at_epoch=time.time() + expires_in - 30)
            self.session.set_bearer_token(token)
            return token
        except Exception as exc:
            warnings.warn(
                f"AuthClient._refresh failed: {exc}. Will fall back to re-authentication.",
                stacklevel=2,
            )
            return None
