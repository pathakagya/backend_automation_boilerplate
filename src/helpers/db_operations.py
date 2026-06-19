"""
Database operations helpers — advanced database utilities for test setup and assertions.

Extends db_helper.py with higher-level operations combining multiple steps.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Optional

from core.db_connection_manager import DatabaseConnection
from helpers.common import qualify_table, get_field
from helpers.db_helper import fetch_row, insert_row, temp_row


def bulk_insert(
    conn: DatabaseConnection,
    table: str,
    rows: list[dict[str, Any]],
    schema: str = "",
) -> int:
    """
    Insert multiple rows and commit in bulk.

    Args:
        conn: Active DatabaseConnection.
        table: Table name.
        rows: List of dicts, each representing a row.
        schema: Optional schema prefix.

    Returns:
        Number of rows inserted.
    """
    count = 0
    for row_data in rows:
        insert_row(conn, table, row_data, schema)
        count += 1
    return count


def bulk_temp_rows(
    conn: DatabaseConnection,
    table: str,
    rows: list[dict[str, Any]],
    schema: str = "",
) -> Generator[list[dict[str, Any]], None, None]:
    """
    Context manager that inserts multiple rows and auto-deletes them after use.

    Args:
        conn: Active DatabaseConnection.
        table: Table name.
        rows: List of row dicts to insert.
        schema: Optional schema prefix.

    Yields:
        The list of rows that were inserted.

    Example:
        with bulk_temp_rows(db, "orders", [row1, row2, row3]) as inserted_rows:
            # test code using the rows
            pass
        # rows are automatically deleted
    """
    inserted = []
    try:
        for row_data in rows:
            insert_row(conn, table, row_data, schema)
            inserted.append(row_data)
        yield inserted
    finally:
        for row_data in inserted:
            qualified = qualify_table(table, schema)
            where = " AND ".join([f"{col}=:{i+1}" for i, col in enumerate(row_data)])
            try:
                conn.execute(
                    f"DELETE FROM {qualified} WHERE {where}",
                    list(row_data.values())
                )
                conn.commit()
            except Exception:
                pass


def fetch_rows_by_field(
    conn: DatabaseConnection,
    table: str,
    field: str,
    value: Any,
    schema: str = "",
) -> list[Any]:
    """
    Fetch all rows where a specific field matches a value.

    Args:
        conn: Active DatabaseConnection.
        table: Table name.
        field: Field name to filter on.
        value: Value to match.
        schema: Optional schema prefix.

    Returns:
        List of matching rows.
    """
    qualified = qualify_table(table, schema)
    query = f"SELECT * FROM {qualified} WHERE {field}=:1"
    return conn.fetch_all(query, [value])


def fetch_by_multiple_fields(
    conn: DatabaseConnection,
    table: str,
    where: dict[str, Any],
    schema: str = "",
) -> list[Any]:
    """
    Fetch all rows matching multiple field conditions.

    Args:
        conn: Active DatabaseConnection.
        table: Table name.
        where: Dict of field:value pairs for WHERE clause.
        schema: Optional schema prefix.

    Returns:
        List of matching rows.
    """
    qualified = qualify_table(table, schema)
    conditions = " AND ".join([f"{col}=:{i+1}" for i, col in enumerate(where)])
    query = f"SELECT * FROM {qualified} WHERE {conditions}"
    return conn.fetch_all(query, list(where.values()))


def row_count(
    conn: DatabaseConnection,
    table: str,
    schema: str = "",
    where: Optional[dict[str, Any]] = None,
) -> int:
    """
    Get row count in a table, optionally filtered by conditions.

    Args:
        conn: Active DatabaseConnection.
        table: Table name.
        schema: Optional schema prefix.
        where: Optional dict of field:value pairs to filter count.

    Returns:
        Number of rows (matching conditions if provided).
    """
    qualified = qualify_table(table, schema)

    if where:
        conditions = " AND ".join([f"{col}=:{i+1}" for i, col in enumerate(where)])
        query = f"SELECT COUNT(*) as cnt FROM {qualified} WHERE {conditions}"
        result = conn.fetch_one(query, list(where.values()))
    else:
        query = f"SELECT COUNT(*) as cnt FROM {qualified}"
        result = conn.fetch_one(query)

    return get_field(result, "cnt", 0)


def table_exists(
    conn: DatabaseConnection,
    table: str,
    schema: str = "",
) -> bool:
    """
    Check if a table exists in the database.

    Note: Implementation is database-specific; this is a basic check.
    May need customization for Oracle, PostgreSQL, etc.

    Args:
        conn: Active DatabaseConnection.
        table: Table name.
        schema: Optional schema prefix.

    Returns:
        True if table exists, False otherwise.
    """
    qualified = qualify_table(table, schema)
    try:
        conn.fetch_one(f"SELECT 1 FROM {qualified} LIMIT 1")
        return True
    except Exception:
        return False


def delete_where(
    conn: DatabaseConnection,
    table: str,
    where: dict[str, Any],
    schema: str = "",
) -> int:
    """
    Delete rows matching conditions and commit.

    Args:
        conn: Active DatabaseConnection.
        table: Table name.
        where: Dict of field:value pairs for WHERE clause.
        schema: Optional schema prefix.

    Returns:
        Number of rows deleted (rowcount from cursor).
    """
    qualified = qualify_table(table, schema)
    conditions = " AND ".join([f"{col}=:{i+1}" for i, col in enumerate(where)])
    query = f"DELETE FROM {qualified} WHERE {conditions}"
    cursor = conn.execute(query, list(where.values()))
    conn.commit()
    return cursor.rowcount if hasattr(cursor, "rowcount") else 0


def update_row(
    conn: DatabaseConnection,
    table: str,
    set_values: dict[str, Any],
    where: dict[str, Any],
    schema: str = "",
) -> int:
    """
    Update rows matching conditions.

    Args:
        conn: Active DatabaseConnection.
        table: Table name.
        set_values: Dict of field:value pairs to update.
        where: Dict of field:value pairs for WHERE clause.
        schema: Optional schema prefix.

    Returns:
        Number of rows updated.
    """
    qualified = qualify_table(table, schema)

    # Build SET clause
    set_clause = ", ".join([f"{k}=:{i+1}" for i, k in enumerate(set_values)])
    set_values_list = list(set_values.values())

    # Build WHERE clause (offset by number of SET values)
    where_offset = len(set_values)
    where_clause = " AND ".join(
        [f"{k}=:{where_offset+i+1}" for i, k in enumerate(where)]
    )
    where_values_list = list(where.values())

    query = f"UPDATE {qualified} SET {set_clause} WHERE {where_clause}"
    cursor = conn.execute(query, set_values_list + where_values_list)
    conn.commit()

    return cursor.rowcount if hasattr(cursor, "rowcount") else 0
