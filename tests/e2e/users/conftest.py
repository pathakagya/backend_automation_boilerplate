"""Fixtures for the Users-module E2E tests (tests/e2e/users/)."""
from __future__ import annotations

import pytest

from api.users_client import UsersClient
from core.api_session_manager import APISession
from core.db_connection_manager import DatabaseConnection
from tests.e2e.users import db_queries


@pytest.fixture(scope="module")
def users_api_client(api_session: APISession) -> UsersClient:
    return UsersClient(api_session)


@pytest.fixture(scope="module")
def lookup_data(db_connection: DatabaseConnection) -> dict:
    """
    Real, currently-valid master-data rows to build FK-valid POST /users payloads with.
    """
    department = db_queries.fetch_one_active_department(db_connection)
    designation = db_queries.fetch_one_active_designation(db_connection)
    area = db_queries.fetch_one_active_area(db_connection)
    probation_status = db_queries.fetch_engagement_status_by_name(db_connection, "Probation")
    existing_user_id = db_queries.fetch_any_existing_user_id(db_connection)
    active_role = db_queries.fetch_one_active_role(db_connection)

    missing = [
        name
        for name, value in (
            ("department", department),
            ("designation", designation),
            ("area", area),
            ("engagement_status(Probation)", probation_status),
            ("existing user", existing_user_id),
        )
        if not value
    ]
    if missing:
        pytest.skip(f"Required lookup/master data not found in the DB: {', '.join(missing)}")

    assert department is not None
    assert designation is not None
    assert area is not None
    assert probation_status is not None

    return {
        "department_id": department["id"],
        "designation_id": designation["id"],
        "designation_name": designation["name"],
        "area_id": area["id"],
        "area_name": area["name"],
        "engagement_status_id": probation_status["id"],
        "engagement_status_name": probation_status["name"],
        "existing_user_id": existing_user_id,
        "active_role": active_role,
    }


# ponytail: cleanup_users removed — direct DB deletes require DELETE access the team
# does not have. Use run_prefix to namespace test data (e.g. username=f"{run_prefix}_alice")
# so stale rows from prior runs do not cause false failures.
