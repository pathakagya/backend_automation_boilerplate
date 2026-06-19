"""
Database test helpers — insert/fetch/compare utilities for test setup and assertions.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Optional

from core.db_connection_manager import DatabaseConnection
from helpers.common import qualify_table, get_field


def insert_row(
    conn: DatabaseConnection,
    table: str,
    data: dict[str, Any],
    schema: str = "",
) -> None:
    """
    Insert a single row and commit.

    Args:
        conn:   Active DatabaseConnection.
        table:  Table name (unqualified).
        data:   Column → value dict.
        schema: Optional schema prefix (e.g. "app_schema").
    """
    qualified = qualify_table(table, schema)
    columns = ", ".join(data.keys())
    placeholders = ", ".join([f":{i+1}" for i in range(len(data))])  # Oracle-style :1,:2
    query = f"INSERT INTO {qualified} ({columns}) VALUES ({placeholders})"
    conn.execute(query, list(data.values()))
    conn.commit()


@contextmanager
def temp_row(
    conn: DatabaseConnection,
    table: str,
    data: dict[str, Any],
    schema: str = "",
    pk_column: str = "id",
) -> Generator[Any, None, None]:
    """
    Context manager that inserts a row and auto-deletes it after the test.

    Usage:
        with temp_row(db, "orders", {"status": "pending"}) as row_data:
            order_id = db.fetch_one("SELECT id FROM orders WHERE status=:1", ["pending"])["id"]
            ...  # test assertions
        # row is deleted automatically
    """
    qualified = qualify_table(table, schema)
    insert_row(conn, table, data, schema)
    try:
        yield data
    finally:
        try:
            where = " AND ".join([f"{col}=:{i+1}" for i, col in enumerate(data)])
            conn.execute(
                f"DELETE FROM {qualified} WHERE {where}",
                list(data.values())
            )
            conn.commit()
        except Exception:
            pass


def fetch_row(
    conn: DatabaseConnection,
    table: str,
    where: dict[str, Any],
    schema: str = "",
) -> Optional[Any]:
    """
    Fetch a single row matching the given column=value pairs.

    Returns None if not found.
    """
    qualified = qualify_table(table, schema)
    conditions = " AND ".join([f"{col}=:{i+1}" for i, col in enumerate(where)])
    query = f"SELECT * FROM {qualified} WHERE {conditions}"
    return conn.fetch_one(query, list(where.values()))


def compare_dicts(expected: dict, actual: dict, fields: Optional[list] = None) -> None:
    """
    Assert that actual contains all key-value pairs in expected.

    Args:
        expected: Dict of field:value pairs you expect.
        actual:   Dict from DB or API response.
        fields:   Subset of keys to compare (defaults to all keys in expected).

    Raises AssertionError with a clear diff on failure.
    """
    fields = fields or list(expected.keys())
    mismatches = {}
    for field in fields:
        exp_val = expected.get(field)
        act_val = get_field(actual, field)
        if exp_val != act_val:
            mismatches[field] = {"expected": exp_val, "actual": act_val}
    if mismatches:
        raise AssertionError(f"Row field mismatches:\n{mismatches}")
