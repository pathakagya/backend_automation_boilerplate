"""
API test helpers — common patterns for making requests and asserting responses.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from requests import Response

from core.api_session_manager import APISession
from helpers.assertions import assert_status
from helpers.response_parser import (
    extract_token,
    extract_list,
    extract_field,
)


def request_and_assert(
    session: APISession,
    method: str,
    path: str,
    expected_status: int = 200,
    **kwargs: Any,
) -> Response:
    """
    Make an HTTP request and assert the status code in one call.

    Args:
        session:         Configured APISession.
        method:          "GET", "POST", "PUT", "PATCH", "DELETE".
        path:            URL path relative to base_url.
        expected_status: Expected HTTP status code.
        **kwargs:        Passed directly to the underlying requests method.

    Returns:
        The requests.Response on success.
    """
    method_fn: Callable = getattr(session, method.lower())
    response: Response = method_fn(path, **kwargs)
    assert_status(response, expected_status)
    return response


# Backward-compatible aliases to response_parser functions
def _extract_token(response: Response) -> Optional[str]:
    """Backward-compatible wrapper for extract_token()."""
    return extract_token(response)


def _extract_list(response: Response, key: str) -> list:
    """Backward-compatible wrapper for extract_list()."""
    return extract_list(response, key)


def _extract_field(response: Response, key: str) -> Any:
    """Backward-compatible wrapper for extract_field()."""
    return extract_field(response, key)


def authenticate_and_set_token(
    session: APISession,
    login_path: str,
    credentials: dict[str, Any],
) -> str:
    """
    POST credentials to login_path, extract the bearer token, and update the session.

    Returns the token string.
    """
    response = request_and_assert(session, "POST", login_path, expected_status=200, json=credentials)
    token = _extract_token(response)
    if not token:
        raise ValueError(
            f"Could not extract a token from {login_path} response: {response.text[:500]}"
        )
    session.set_bearer_token(token)
    return token


def paginate_all(
    session: APISession,
    path: str,
    items_key: str = "data",
    next_key: str = "next",
    params: Optional[dict] = None,
    max_pages: int = 50,
) -> list[Any]:
    """
    Follow cursor/page-based pagination and collect all items.

    Args:
        session:    APISession.
        path:       Starting URL path.
        items_key:  JSON key that holds the list of items.
        next_key:   JSON key that holds the next page URL/cursor (None = last page).
        params:     Query parameters for the first request.
        max_pages:  Safety limit to prevent infinite loops.

    Returns:
        Flat list of all items across all pages.
    """
    all_items: list = []
    current_path = path
    current_params = dict(params or {})
    pages_fetched = 0

    while current_path and pages_fetched < max_pages:
        response = request_and_assert(session, "GET", current_path, params=current_params)
        items = _extract_list(response, items_key)
        all_items.extend(items)
        pages_fetched += 1

        next_cursor = _extract_field(response, next_key)
        if not next_cursor:
            break
        # If next_cursor is a full URL, use it directly; otherwise append to base
        if str(next_cursor).startswith("http"):
            current_path = next_cursor
            current_params = {}
        else:
            current_params["cursor"] = next_cursor

    return all_items
