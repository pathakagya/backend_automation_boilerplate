"""
Custom assertion helpers — readable test assertions with descriptive failure messages.

All functions raise AssertionError with context when they fail so Allure
and pytest capture exactly what went wrong.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from requests import Response

from core.constants import SmokeExpectedStatus, SmokeTimeoutSeconds
from helpers.common import get_field


# ---------------------------------------------------------------------------
# HTTP / API assertions
# ---------------------------------------------------------------------------

def assert_status(response: Response, expected: int) -> None:
    """Assert HTTP status code equals an explicit expected value."""
    actual = response.status_code
    if actual != expected:
        body = _safe_body(response)
        raise AssertionError(
            f"Expected status {expected}, got {actual}.\n"
            f"URL: {response.url}\nBody: {body}"
        )


def assert_response_status(response: Response, module_name: str) -> None:
    """Assert response status using module-based defaults."""
    expected = SmokeExpectedStatus.BY_MODULE.get(module_name, SmokeExpectedStatus.DEFAULT)
    actual = response.status_code
    if actual != expected:
        body = _safe_body(response)
        raise AssertionError(
            f"[{module_name}] Expected status {expected}, got {actual}.\n"
            f"URL: {response.url}\nBody: {body}"
        )


def assert_response_time(response: Response, module_name: str) -> None:
    """Assert response elapsed time using module-based timeout thresholds."""
    threshold = SmokeTimeoutSeconds.BY_MODULE.get(module_name, SmokeTimeoutSeconds.DEFAULT)
    elapsed = response.elapsed.total_seconds()
    if elapsed > threshold:
        raise AssertionError(
            f"[{module_name}] Response time {elapsed:.3f}s exceeded threshold {threshold:.3f}s.\n"
            f"URL: {response.url}"
        )


def assert_field(response: Response, key: str, expected: Any = None) -> Any:
    """
    Assert a JSON response body contains key (and optionally matches expected value).

    Returns the field value for further assertions.
    """
    data = _parse_json(response)
    if key not in data:
        raise AssertionError(
            f"Expected field {key!r} in response but it was missing.\nBody: {data}"
        )
    actual = data[key]
    if expected is not None and actual != expected:
        raise AssertionError(
            f"Field {key!r}: expected {expected!r}, got {actual!r}."
        )
    return actual


def assert_list_not_empty(response: Response, key: Optional[str] = None) -> list:
    """Assert the response (or a specific key within it) is a non-empty list."""
    data = _parse_json(response)
    target = data[key] if key else data
    if not isinstance(target, list) or len(target) == 0:
        raise AssertionError(
            f"Expected a non-empty list{f' at key {key!r}' if key else ''}, got {target!r}."
        )
    return target


# ---------------------------------------------------------------------------
# Database assertions
# ---------------------------------------------------------------------------

def assert_row_exists(row: Optional[Any], label: str = "DB row") -> None:
    """Assert that a DB fetch result is not None / empty."""
    if row is None:
        raise AssertionError(f"{label}: expected to find a row but got None.")


def assert_row_count(rows: list, expected: int, label: str = "DB rows") -> None:
    """Assert the number of rows returned equals expected."""
    actual = len(rows)
    if actual != expected:
        raise AssertionError(
            f"{label}: expected {expected} rows, got {actual}."
        )


def assert_row_field(row: Any, field: str, expected: Any) -> None:
    """
    Assert a specific field in a DB row matches expected.
    Supports both dict rows and namedtuple/Row objects.
    """
    actual = get_field(row, field)
    if actual != expected:
        raise AssertionError(
            f"Row field {field!r}: expected {expected!r}, got {actual!r}."
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_body(response: Response) -> str:
    """Return a compact response body for assertion diagnostics."""
    try:
        return json.dumps(response.json(), indent=2)
    except Exception:
        return response.text[:2000]


def _parse_json(response: Response) -> Any:
    """Decode a JSON response or raise a useful assertion error."""
    try:
        return response.json()
    except Exception as exc:
        raise AssertionError(
            f"Response body is not valid JSON: {response.text[:500]}"
        ) from exc
