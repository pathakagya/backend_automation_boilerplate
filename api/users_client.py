"""
Typed API client for the Users module, used by tests/e2e/users/test_create_user.py.

See .claude/skills/generate-api-client/SKILL.md to scaffold one for another module.
"""
from __future__ import annotations

from typing import Any

import requests

from api.base_client import BaseAPIClient
from core.constants import APIPath


class UsersClient(BaseAPIClient):
    """Typed HTTP client for /core/users endpoints."""

    def create_user(self, payload: dict[str, Any], **kwargs: Any) -> requests.Response:
        """Create one Vyaguta user with a verified POST /core/users payload."""
        return self.post(APIPath.USERS, json=payload, **kwargs)

    def get_user(self, user_id: int, **kwargs: Any) -> requests.Response:
        """Fetch one user by numeric identifier."""
        return self.get_path(APIPath.USER_BY_ID, {"id": user_id}, **kwargs)

    def update_user(self, user_id: int, payload: dict[str, Any], **kwargs: Any) -> requests.Response:
        """Update one user using the verified PUT /core/users/{id} endpoint."""
        return self.put_path(APIPath.USER_BY_ID, {"id": user_id}, json=payload, **kwargs)

    def get_user_count(self, **kwargs: Any) -> requests.Response:
        """Fetch the Users aggregate count used by smoke/integration examples."""
        return self.get(APIPath.USER_COUNT, **kwargs)

    def get_user_summary(self, **kwargs: Any) -> requests.Response:
        """Fetch the Users summary aggregate used by smoke examples."""
        return self.get(APIPath.USER_SUMMARY, **kwargs)

    def update_designation(self, user_id: int, payload: dict[str, Any], **kwargs: Any) -> requests.Response:
        """Update a user's designation using the verified nested endpoint."""
        return self.put_path(APIPath.USER_DESIGNATION, {"id": user_id}, json=payload, **kwargs)

    def update_engagement_status(self, user_id: int, payload: dict[str, Any], **kwargs: Any) -> requests.Response:
        """Update a user's engagement status using the verified nested endpoint."""
        return self.put_path(APIPath.USER_ENGAGEMENT_STATUS, {"id": user_id}, json=payload, **kwargs)

    def get_user_roles(self, user_id: int, **kwargs: Any) -> requests.Response:
        """Fetch roles assigned to one user."""
        return self.get_path(APIPath.USER_ROLES, {"id": user_id}, **kwargs)

    def add_user_roles(self, user_id: int, payload: dict[str, Any], **kwargs: Any) -> requests.Response:
        """Assign roles to one user using the verified nested endpoint."""
        return self.post_path(APIPath.USER_ROLES, {"id": user_id}, json=payload, **kwargs)

    def activate_user(self, user_id: int, **kwargs: Any) -> requests.Response:
        """Activate one user using the verified nested endpoint."""
        return self.post_path(APIPath.USER_ACTIVATE, {"id": user_id}, **kwargs)
