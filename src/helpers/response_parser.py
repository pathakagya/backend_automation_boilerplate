"""
Response parser helpers — extract and parse data from HTTP responses.

Consolidates common response extraction patterns used across API helpers.
"""
from __future__ import annotations

from typing import Any, Optional

from requests import Response


def extract_field(response: Response, key: str, default: Any = None) -> Any:
    """
    Extract a field from the JSON response body.

    Args:
        response: The HTTP response object.
        key: JSON key to extract.
        default: Default value if key is not found or response is not JSON.

    Returns:
        The field value, or default if not found.
    """
    try:
        body = response.json()
        return body.get(key, default) if isinstance(body, dict) else default
    except Exception:
        return default


def extract_list(response: Response, key: str) -> list:
    """
    Extract a list from a specific key in the JSON response body.

    Args:
        response: The HTTP response object.
        key: JSON key containing the list.

    Returns:
        The list value, or empty list if not found or not a list.
    """
    try:
        body = response.json()
        value = body.get(key) if isinstance(body, dict) else None
        return value if isinstance(value, list) else []
    except Exception:
        return []


def extract_token(response: Response) -> Optional[str]:
    """
    Extract a bearer token from the response body.

    Searches for common token field names:
    - At root level: token, access_token, accessToken
    - Under 'data' key: token, access_token, accessToken

    Args:
        response: The HTTP response object (typically from a login endpoint).

    Returns:
        The token string if found, None otherwise.
    """
    try:
        body = response.json()
    except Exception:
        return None

    # Check root level
    for key in ("token", "access_token", "accessToken"):
        if key in body:
            return body[key]

    # Check under 'data' key
    data = body.get("data") or {}
    if isinstance(data, dict):
        for key in ("token", "access_token", "accessToken"):
            if key in data:
                return data[key]

    return None


def extract_nested_field(response: Response, path: str, separator: str = ".") -> Any:
    """
    Extract a nested field using dot notation or custom separator.

    Args:
        response: The HTTP response object.
        path: Nested key path (e.g., "data.user.id" or "result|item|name").
        separator: Path separator (default ".").

    Returns:
        The nested field value, or None if not found.

    Example:
        token = extract_nested_field(response, "data.auth.token")
        user_id = extract_nested_field(response, "result|user|id", separator="|")
    """
    try:
        body = response.json()
        keys = path.split(separator)

        current = body
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None

        return current
    except Exception:
        return None


def extract_all_matching(response: Response, predicate) -> list:
    """
    Extract all items from a list response matching a predicate.

    Args:
        response: The HTTP response object.
        predicate: Function that returns True for items to include.

    Returns:
        List of matching items.

    Example:
        active_users = extract_all_matching(
            response,
            lambda item: item.get("status") == "active"
        )
    """
    try:
        body = response.json()
        items = body if isinstance(body, list) else body.get("data", [])

        if isinstance(items, list):
            return [item for item in items if predicate(item)]
        return []
    except Exception:
        return []
