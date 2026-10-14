"""
BaseAPIClient: thin, typed wrapper for organizing HTTP calls into per-resource clients.

Wraps an existing, already-authenticated APISession (never builds a second session) and adds:
    - one method per endpoint, named after the business action, not the HTTP verb
    - "{param}"-style path-parameter substitution, matching core.constants.APIPath's own
      "{id}"-style templates
    - appended path segments for endpoints without a fixed template
    - a raw URL resolver for helpers that need a full URL string (e.g. pagination)

Retry, timeout, and Allure request/response attachment are all handled by the wrapped
APISession — this class adds no request-dispatch logic of its own beyond routing each
business action to the right path.

Usage:
    from api.base_client import BaseAPIClient
    from core.constants import APIPath

    class OrdersClient(BaseAPIClient):
        def create_order(self, payload, **kwargs):
            return self.post(APIPath.ORDERS, json=payload, **kwargs)

        def get_order(self, order_id, **kwargs):
            return self.get_path(APIPath.ORDER_BY_ID, {"id": order_id}, **kwargs)

    orders_client = OrdersClient(api_session)
    response = orders_client.get_order(42)
"""
from __future__ import annotations

from typing import Any

import requests

from core.api_session_manager import APISession


class BaseAPIClient:
    """Extend this for every typed, per-resource API client. See .claude/rules/api-standards.md."""

    def __init__(self, api_session: APISession) -> None:
        self._api_session = api_session

    @property
    def base_url(self) -> str:
        """Return the wrapped session's normalized API base URL."""
        return self._api_session.base_url

    @property
    def session(self) -> APISession:
        """The wrapped APISession — for escape hatches like pagination link-following."""
        return self._api_session

    # ------------------------------------------------------------------ #
    # Plain HTTP verbs
    # ------------------------------------------------------------------ #

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self._api_session.get(path, **kwargs)

    def post(self, path: str, json: Any = None, **kwargs: Any) -> requests.Response:
        return self._api_session.post(path, json=json, **kwargs)

    def put(self, path: str, json: Any = None, **kwargs: Any) -> requests.Response:
        return self._api_session.put(path, json=json, **kwargs)

    def patch(self, path: str, json: Any = None, **kwargs: Any) -> requests.Response:
        return self._api_session.patch(path, json=json, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self._api_session.delete(path, **kwargs)

    # ------------------------------------------------------------------ #
    # Path-parameter / appended-segment convenience
    # ------------------------------------------------------------------ #

    def get_path(self, path_template: str, path_params: dict[str, Any], **kwargs: Any) -> requests.Response:
        """GET with "{param}" substitution, e.g. get_path(APIPath.USER_BY_ID, {"id": 42})."""
        return self._api_session.get(path_template.format(**path_params), **kwargs)

    def post_path(self, path_template: str, path_params: dict[str, Any], json: Any = None, **kwargs: Any) -> requests.Response:
        """POST with "{param}" substitution."""
        return self._api_session.post(path_template.format(**path_params), json=json, **kwargs)

    def put_path(self, path_template: str, path_params: dict[str, Any], json: Any = None, **kwargs: Any) -> requests.Response:
        """PUT with "{param}" substitution."""
        return self._api_session.put(path_template.format(**path_params), json=json, **kwargs)

    def patch_path(self, path_template: str, path_params: dict[str, Any], json: Any = None, **kwargs: Any) -> requests.Response:
        """PATCH with "{param}" substitution."""
        return self._api_session.patch(path_template.format(**path_params), json=json, **kwargs)

    def delete_path(self, path_template: str, path_params: dict[str, Any], **kwargs: Any) -> requests.Response:
        """DELETE with "{param}" substitution."""
        return self._api_session.delete(path_template.format(**path_params), **kwargs)

    def get_with_path(self, path: str, *segments: Any, **kwargs: Any) -> requests.Response:
        """GET with extra segments appended, e.g. get_with_path(APIPath.USERS, 42, "roles")."""
        clean_segments = [str(s).strip("/") for s in segments]
        full_path = "/".join([path.rstrip("/")] + clean_segments)
        return self._api_session.get(full_path, **kwargs)

    def url_for(self, path_template: str, **path_params: Any) -> str:
        """Resolve a full URL string — for helpers that need session.get(raw_url) directly."""
        path = path_template.format(**path_params) if path_params else path_template
        return self._api_session.build_url(path)
