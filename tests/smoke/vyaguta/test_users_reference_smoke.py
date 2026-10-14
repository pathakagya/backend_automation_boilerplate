"""Worked Vyaguta smoke examples for the Users API."""
from __future__ import annotations

import allure
import pytest

from api.users_client import UsersClient
from core.constants import DBTable, HTTPStatus, SmokeModule
from tests.commons.assertions import assert_response_time, assert_status

pytestmark = pytest.mark.smoke


@allure.feature("Vyaguta Users reference")
class TestVyagutaUsersSmoke:
    """Show how a project-specific typed client is used in smoke tests."""

    @allure.title("Users count endpoint is reachable")
    def test_users_count_endpoint(self, api_session):
        """Verify the documented Users count endpoint returns a successful response."""
        client = UsersClient(api_session)

        with allure.step("GET /core/users/count"):
            response = client.get_user_count()

        assert_status(response, HTTPStatus.OK)
        assert_response_time(response, SmokeModule.GENERIC_GET)

    @allure.title("Users summary endpoint is reachable")
    def test_users_summary_endpoint(self, api_session):
        """Verify the documented Users summary endpoint returns a successful response."""
        client = UsersClient(api_session)

        with allure.step("GET /core/users/summary"):
            response = client.get_user_summary()

        assert_status(response, HTTPStatus.OK)
        assert_response_time(response, SmokeModule.GENERIC_GET)

    @pytest.mark.db_required
    @allure.title("Vyaguta Users master tables are accessible")
    def test_users_master_tables_are_accessible(self, db_connection):
        """Verify the reference Users and Roles tables are available to DB tests."""
        for table in (DBTable.USER, DBTable.ROLES):
            with allure.step(f"Query {table}"):
                row = db_connection.fetch_one(f"SELECT 1 AS ok FROM {table} LIMIT 1")
            assert row["ok"] == 1, f"Expected to access reference table {table}"

