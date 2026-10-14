"""
Module-level DB query helpers for the Users-module E2E tests.

Why this module exists alongside the tests (not in helpers/):
  These are Users-module-specific reads. Generic single-table equality reads use
  helpers.db_helper.fetch_row; multi-row reads use helpers.db_operations.fetch_rows_by_field.
  Only queries that cannot be expressed by those helpers live here:
    - fetch_non_existent_id: requires MAX() aggregate
    - fetch_any_existing_user_id: no WHERE clause, ORDER BY only
    - count_rows: thin wrapper preserving the isolation commit before the count

Why every read calls _start_fresh_read first:
  db_connection is session-scoped and opened with autocommit=False. MySQL's default
  isolation level is REPEATABLE READ — once any statement runs on this connection it
  holds a snapshot frozen at that moment. A later SELECT on the SAME connection will
  NOT see rows another connection (the API under test) committed afterward, even though
  they exist. Committing before every read ends the stale transaction so the next
  statement opens a fresh snapshot. Confirmed live: a POST /users returning 201 was
  immediately followed by a fetch returning None for that id until the commit was added.
  See also: docs/DATABASE_SETUP.md §"Transaction isolation".

Table/column reference: core.constants.DBTable.
"""
from __future__ import annotations

from typing import Any, Optional

from core.constants import DBTable
from core.db_connection_manager import DatabaseConnection
from helpers.db_helper import fetch_row
from helpers.db_operations import fetch_rows_by_field, row_count


def _start_fresh_read(conn: DatabaseConnection) -> None:
    """End any open (possibly stale) transaction so the next statement sees latest-committed data."""
    conn.commit()


# ---------------------------------------------------------------------------
# Lookup / master data (used to build valid FK references in test payloads)
# ---------------------------------------------------------------------------

def fetch_one_active_department(conn: DatabaseConnection) -> Optional[dict]:
    _start_fresh_read(conn)
    return fetch_row(conn, DBTable.DEPARTMENT, {"status": 1})


def fetch_one_active_designation(conn: DatabaseConnection) -> Optional[dict]:
    _start_fresh_read(conn)
    return fetch_row(conn, DBTable.DESIGNATION, {"status": 1})


def fetch_one_active_area(conn: DatabaseConnection) -> Optional[dict]:
    _start_fresh_read(conn)
    return fetch_row(conn, DBTable.AREA, {"is_active": 1})


def fetch_engagement_status_by_name(conn: DatabaseConnection, name: str) -> Optional[dict]:
    _start_fresh_read(conn)
    return fetch_row(conn, DBTable.ENGAGEMENT_STATUS, {"name": name})


def fetch_one_active_role(conn: DatabaseConnection) -> Optional[dict]:
    _start_fresh_read(conn)
    return fetch_row(conn, DBTable.ROLES, {"is_active": 1})


def fetch_any_existing_user_id(conn: DatabaseConnection) -> Optional[int]:
    """
    Any existing user.id is valid as a leaveIssuerId/teamManagerId/appraiserId FK reference.
    No WHERE clause — needs ORDER BY only, so cannot use fetch_row.
    """
    _start_fresh_read(conn)
    row = conn.fetch_one(f"SELECT id FROM {DBTable.USER} ORDER BY id LIMIT 1")
    return row["id"] if row else None


def fetch_non_existent_id(conn: DatabaseConnection, table: str) -> int:
    """Return an id guaranteed not to exist in `table`, for invalid-FK negative cases."""
    _start_fresh_read(conn)
    row = conn.fetch_one(f"SELECT MAX(id) AS max_id FROM {table}")
    max_id = (row or {}).get("max_id") or 0
    return int(max_id) + 1_000_000


# ---------------------------------------------------------------------------
# Post-create verification reads
# ---------------------------------------------------------------------------

def fetch_user(conn: DatabaseConnection, user_id: int) -> Optional[dict]:
    _start_fresh_read(conn)
    return fetch_row(conn, DBTable.USER, {"id": user_id})


def fetch_user_by_username(conn: DatabaseConnection, username: str) -> Optional[dict]:
    _start_fresh_read(conn)
    return fetch_row(conn, DBTable.USER, {"username": username})


def fetch_emp_status_rows(conn: DatabaseConnection, user_id: int) -> list[dict]:
    _start_fresh_read(conn)
    return fetch_rows_by_field(conn, DBTable.EMP_STATUS, "user_id", user_id, order_by="transition_date")


def fetch_emp_status_details_rows(conn: DatabaseConnection, emp_status_id: int) -> list[dict]:
    _start_fresh_read(conn)
    return fetch_rows_by_field(conn, DBTable.EMP_STATUS_DETAILS, "emp_status_id", emp_status_id, order_by="date")


def fetch_emp_designation_area_rows(conn: DatabaseConnection, user_id: int) -> list[dict]:
    _start_fresh_read(conn)
    return fetch_rows_by_field(conn, DBTable.EMP_DESIGNATION_AREA, "user_id", user_id, order_by="transition_date")


def fetch_emp_leave_issuer_rows(conn: DatabaseConnection, user_id: int) -> list[dict]:
    _start_fresh_read(conn)
    return fetch_rows_by_field(conn, DBTable.EMP_LEAVE_ISSUERS, "user_id", user_id, order_by="transition_date")


def fetch_emp_team_manager_rows(conn: DatabaseConnection, user_id: int) -> list[dict]:
    _start_fresh_read(conn)
    return fetch_rows_by_field(conn, DBTable.EMP_TEAM_MANAGERS, "user_id", user_id, order_by="transition_date")


def fetch_roles_users_rows(conn: DatabaseConnection, user_id: int) -> list[dict]:
    _start_fresh_read(conn)
    return fetch_rows_by_field(conn, DBTable.ROLES_USERS, "user_id", user_id)


def fetch_attendance_leave_credit_rows(conn: DatabaseConnection, user_id: int) -> list[dict]:
    _start_fresh_read(conn)
    return fetch_rows_by_field(conn, DBTable.ATTENDANCE_LEAVE_CREDITS, "user_id", user_id)


def fetch_teams_allocation_rows(conn: DatabaseConnection, user_id: int) -> list[dict]:
    _start_fresh_read(conn)
    return fetch_rows_by_field(conn, DBTable.TEAMS_ALLOCATIONS, "user_id", user_id)


def count_rows(conn: DatabaseConnection, table: str, where_col: str, value: Any) -> int:
    _start_fresh_read(conn)
    return row_count(conn, table, where={where_col: value})
