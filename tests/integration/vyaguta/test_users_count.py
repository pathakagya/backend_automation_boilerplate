"""Worked API-to-DB count-parity example for Vyaguta Users."""
from __future__ import annotations

import allure
import pytest

from api.users_client import UsersClient
from core.constants import DBTable, HTTPStatus
from helpers.db_operations import row_count
from helpers.integration import assert_api_db_count
from tests.commons.assertions import assert_status

pytestmark = [pytest.mark.integration, pytest.mark.db_required]


@allure.feature("Vyaguta Users reference")
class TestVyagutaUsersCount:
    """Show a read-only integration test using a typed client and DB query."""

    @allure.title("Users count matches the database")
    def test_users_count_matches_db(self, api_session, db_connection):
        """Compare the Users API ``count`` field with the reference DB table count."""
        client = UsersClient(api_session)

        with allure.step("GET /core/users/count"):
            response = client.get_user_count()
        assert_status(response, HTTPStatus.OK)

        with allure.step(f"COUNT rows in {DBTable.USER}"):
            db_count = row_count(db_connection, DBTable.USER)
        api_count = response.json()["data"]["count"]
        with allure.step("Compare API and DB counts"):
            assert_api_db_count(
                api_count,
                db_count,
                label="Vyaguta users",
            )

