"""Generic API-to-database integration-test helpers."""
from __future__ import annotations

from typing import Any


def extract_collection_count(
    payload: Any,
    *,
    items_key: str | None = None,
    total_key: str | None = None,
) -> int:
    """Extract an API collection count from a payload, collection, or scalar.

    Args:
        payload: Decoded JSON response, collection list, or already-extracted
            integer count.
        items_key: Optional list field containing collection items.
        total_key: Optional server-provided total field.

    Returns:
        The server-provided total when configured, otherwise the item count.

    Raises:
        AssertionError: If the configured fields are absent or have invalid types.
    """
    if isinstance(payload, int) and not isinstance(payload, bool):
        return payload
    if total_key and isinstance(payload, dict):
        total = payload.get(total_key) if isinstance(payload, dict) else None
        if isinstance(total, int):
            return total
    target = payload.get(items_key) if items_key and isinstance(payload, dict) else payload
    if not isinstance(target, list):
        raise AssertionError(
            f"Expected a collection list at {items_key or '<response>'!r}, got {target!r}"
        )
    return len(target)


def assert_api_db_count(
    api_payload: Any,
    db_count: int,
    *,
    items_key: str | None = None,
    total_key: str | None = None,
    label: str = "collection",
) -> None:
    """Assert an API count equals an independently queried DB count.

    ``api_payload`` may be a complete response payload, a collection, or a
    verified scalar count extracted by a project-specific client/test.
    """
    api_count = extract_collection_count(
        api_payload, items_key=items_key, total_key=total_key
    )
    if api_count != db_count:
        raise AssertionError(
            f"{label} count mismatch: API returned {api_count}, DB returned {db_count}"
        )

