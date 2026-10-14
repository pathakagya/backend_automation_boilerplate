"""
Database test helpers — insert/fetch/compare utilities for test setup and assertions.
"""
from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Any, Generator, Optional

from core.db_connection_manager import DatabaseConnection
from helpers.common import placeholder, qualify_table, get_field


def insert_row(
    conn: DatabaseConnection,
    table: str,
    data: dict[str, Any],
    schema: str = "",
    autocommit: bool = True,
) -> Any:
    """
    Insert a single row.

    Args:
        conn:        Active DatabaseConnection.
        table:       Table name (unqualified).
        data:        Column → value dict.
        schema:      Optional schema prefix (e.g. "app_schema").
        autocommit:  Commit immediately after the insert (default True). Pass False
                     when calling inside a transaction block or bulk loop — the caller
                     is then responsible for committing.

    Returns:
        The inserted row's auto-generated primary key (cursor.lastrowid), or None if the
        driver/table doesn't expose one (e.g. no auto-increment column).
    """
    qualified = qualify_table(table, schema)
    columns = ", ".join(data.keys())
    placeholders = ", ".join(placeholder(conn.paramstyle, i + 1) for i in range(len(data)))
    query = f"INSERT INTO {qualified} ({columns}) VALUES ({placeholders})"
    cursor = conn.execute(query, list(data.values()))
    if autocommit:
        conn.commit()
    return getattr(cursor, "lastrowid", None)


@contextmanager
def temp_row(
    conn: DatabaseConnection,
    table: str,
    data: dict[str, Any],
    schema: str = "",
    pk_column: str = "id",
) -> Generator[dict[str, Any], None, None]:
    """
    Context manager that inserts a row and auto-deletes it after the test.

    Deletes by `pk_column` using the inserted row's auto-generated id, not by matching the
    original column values — matching on values would also delete any other row that happens
    to share them.

    Usage:
        with temp_row(db, "orders", {"status": "pending"}) as row_data:
            order_id = row_data[pk_column]
            ...  # test assertions
        # row is deleted automatically
    """
    qualified = qualify_table(table, schema)
    inserted_id = insert_row(conn, table, data, schema)
    pk_value = data.get(pk_column, inserted_id)  # an explicit pk in `data` wins over lastrowid
    row_data = {**data, pk_column: pk_value} if pk_value is not None else dict(data)
    try:
        yield row_data
    finally:
        try:
            if pk_value is not None:
                conn.execute(
                    f"DELETE FROM {qualified} WHERE {pk_column}={placeholder(conn.paramstyle, 1)}",
                    [pk_value],
                )
            else:
                # No PK available (driver/table doesn't expose lastrowid) — fall back to a
                # full-value match, which can also delete other rows sharing those values.
                where = " AND ".join(
                    f"{col}={placeholder(conn.paramstyle, i + 1)}" for i, col in enumerate(data)
                )
                conn.execute(
                    f"DELETE FROM {qualified} WHERE {where}",
                    list(data.values())
                )
            conn.commit()
        except Exception as exc:
            warnings.warn(
                f"temp_row teardown: failed to delete row {pk_column}={pk_value!r} "
                f"from {qualified}: {exc}. Stale row may persist.",
                stacklevel=2,
            )


def fetch_row(
    conn: DatabaseConnection,
    table: str,
    where: dict[str, Any],
    schema: str = "",
    order_by: str = "",
) -> Optional[Any]:
    """
    Fetch a single row matching the given column=value pairs.

    Args:
        conn: Active DatabaseConnection.
        table: Table name.
        where: Column → value equality conditions.
        schema: Optional schema prefix.
        order_by: Optional column name(s) for ORDER BY (e.g. "id", "created_at DESC").
                  Useful when multiple rows could match and you want the first by a specific order.

    Returns None if not found.
    """
    qualified = qualify_table(table, schema)
    conditions = " AND ".join(
        f"{col}={placeholder(conn.paramstyle, i + 1)}" for i, col in enumerate(where)
    )
    query = f"SELECT * FROM {qualified} WHERE {conditions}"
    if order_by:
        query += f" ORDER BY {order_by}"
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
