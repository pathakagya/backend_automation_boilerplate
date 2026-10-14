"""Small worked E2E example for the current boilerplate conventions.
"""
from __future__ import annotations

import allure
import pytest

from core.constants import HTTPStatus
from tests.commons.assertions import assert_field, assert_row_exists, assert_status, assert_row_field
from tests.commons.data_builder import UserFactory
from tests.e2e.users import db_queries

pytestmark = [pytest.mark.e2e, pytest.mark.db_required]


@allure.feature("Vyaguta Users reference")
class TestUserWorkflowExample:
    """Demonstrate a minimal API create, DB verification, and API read-back flow."""

    def test_create_persist_and_read_user(
        self, users_api_client, db_connection, lookup_data, run_prefix
    ):
        """Create a user, verify persistence, then fetch it through the API."""
        payload = UserFactory.create_payload(
            department_id=lookup_data["department_id"],
            designation_id=lookup_data["designation_id"],
            designation_name=lookup_data["designation_name"],
            area_id=lookup_data["area_id"],
            area_name=lookup_data["area_name"],
            engagement_status_id=lookup_data["engagement_status_id"],
            engagement_status_name=lookup_data["engagement_status_name"],
            team_manager_id=lookup_data["existing_user_id"],
            appraiser_id=lookup_data["existing_user_id"],
        )

        with allure.step("Create the user through the typed API client"):
            create_response = users_api_client.create_user(payload)
        assert_status(create_response, HTTPStatus.CREATED)
        user_id = assert_field(create_response, "data")["id"]

        with allure.step("Verify the user row exists in the database"):
            row = db_queries.fetch_user(db_connection, user_id)
        assert_row_exists(row, label=f"user id={user_id}")
        assert_row_field(row, "username", payload["username"])

        with allure.step("Read the created user through the API"):
            read_response = users_api_client.get_user(user_id)
        assert_status(read_response, HTTPStatus.OK)
        assert_field(read_response, "data")

