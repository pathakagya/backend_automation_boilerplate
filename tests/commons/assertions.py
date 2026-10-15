"""
Project-facing assertion helpers — import assertions for tests from here, not from
`helpers.assertions` directly (see `.claude/rules/assertions.md`).

Generic HTTP/DB primitives (assert_status, assert_row_exists, ...) are defined once in
`helpers.assertions` (boilerplate layer, reusable across any fork) and re-exported below.
This module adds the composed assertions that only make sense once a project has real API
response shapes and DB tables to validate against: API/DB sync and response-schema validation.
"""
from __future__ import annotations

from typing import Any, Optional

from helpers.assertions import (
    assert_field,
    assert_list_not_empty,
    assert_response_status,
    assert_response_time,
    assert_row_count,
    assert_row_exists,
    assert_row_field,
    assert_status,
)
from helpers.common import get_field

__all__ = [
    "assert_status",
    "assert_response_status",
    "assert_response_time",
    "assert_field",
    "assert_list_not_empty",
    "assert_row_exists",
    "assert_row_count",
    "assert_row_field",
    "assert_api_db_sync",
    "assert_response_schema",
]


# ---------------------------------------------------------------------------
# API / DB sync
# ---------------------------------------------------------------------------

def _normalize_db_value(db_value: Any, api_value: Any) -> Any:
    """
    Undo DB-driver quirks on the DB side only, guided by the API value's type.

    Handles: trailing whitespace on CHAR-padded text columns, boolean columns returned as
    "1"/"0", and numeric columns returned as strings. The API value is never coerced, so an
    API that sends "12345" where the DB holds 12345 still fails — that is a real contract bug.
    Do NOT cast either side to str() before calling assert_api_db_sync.
    """
    if not isinstance(db_value, str):
        return db_value
    stripped = db_value.strip()
    if isinstance(api_value, bool):
        return stripped == "1" if stripped in ("1", "0") else stripped
    if isinstance(api_value, (int, float)):
        for cast in (int, float):
            try:
                return cast(stripped)
            except ValueError:
                pass
    return stripped


def assert_api_db_sync(
    api_record: dict[str, Any],
    db_record: Any,
    field_mapping: dict[str, str],
) -> None:
    """
    Assert that selected API response fields match their corresponding DB columns.

    `field_mapping` maps API field name -> DB column name explicitly, so the mapping stays
    readable instead of positional:

        assert_api_db_sync(
            api_record=response.json()["data"],
            db_record=user_row,
            field_mapping={"username": "username", "departmentId": "department_id"},
        )

    DB values are normalised before comparison (see _normalize_db_value) — never str() either
    side yourself first.
    """
    mismatches: dict[str, dict[str, Any]] = {}
    for api_field, db_column in field_mapping.items():
        api_value = get_field(api_record, api_field)
        db_value = _normalize_db_value(get_field(db_record, db_column), api_value)
        if api_value != db_value:
            mismatches[api_field] = {
                "api_value": api_value,
                "db_column": db_column,
                "db_value": db_value,
            }
    if mismatches:
        raise AssertionError(f"API/DB field mismatches:\n{mismatches}")


# ---------------------------------------------------------------------------
# Response schema validation
# ---------------------------------------------------------------------------

def assert_response_schema(
    record: dict[str, Any],
    schema: dict[str, Any],
    optional_fields: Optional[set] = None,
) -> None:
    """
    Assert `record`'s fields are present and type-correct per `schema`.

    `schema` is a plain dict mapping field name -> expected type or tuple of types, e.g.
    `{"id": int, "email": (str, type(None))}` — a tuple including `type(None)` marks a field as
    *nullable* (present, value may be None). Pass a field name in `optional_fields` to mark it as
    allowed to be *absent* from `record` entirely — nullable and optional are different things.

    Collects every mismatch before raising (not fail-fast on the first one) so a broad contract
    break shows its full extent in one failure message, not one-field-at-a-time reruns.
    """
    optional_fields = optional_fields or set()
    errors: list[str] = []
    for field, expected_type in schema.items():
        if field not in record:
            if field not in optional_fields:
                errors.append(f"{field!r}: missing from record")
            continue
        if not isinstance(record[field], expected_type):
            errors.append(
                f"{field!r}: expected type {expected_type}, got {type(record[field])} "
                f"(value={record[field]!r})"
            )
    if errors:
        raise AssertionError("Response schema validation failed:\n" + "\n".join(errors))
