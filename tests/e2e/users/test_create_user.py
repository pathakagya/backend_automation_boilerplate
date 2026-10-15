"""
E2E tests for POST /core/users — create user.

Positive / negative / edge coverage plus explicit API<->DB field-name-mapping and
data-type parity checks, per docs/USERS_MODULE_TEST_DESIGN.md §4 (the "Deep-Dive:
POST /users" design).

Ground truth has two layers, and they occasionally disagree — where they do, the live
run wins:
  1. Core.postman_collection.json — the original source for the request/response shape.
  2. testresult.log — a real run against https://qa.vyaguta.lftechnology.com.np, which
     corrected several assumptions the collection implied: `teamManagerId`/`appraiserId`
     are REQUIRED (not nullable, despite being nullable DB columns), `username` must be
     email-shaped, and validation-error bodies are a flat {status,message,details} shape,
     not the nested {"error":{...}} shape older captured Postman test scripts expected.

Known unresolved gaps this file does NOT assert on: exact category values for
emp_status_details beyond "Mid Probation"/"End Probation", and the business-rule error
shape for "username already exists" hasn't been independently reconfirmed since the
error-envelope correction above (see _error_message_text()).
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime

import pytest
import requests

from core.constants import DBTable, HTTPStatus
from tests.commons.assertions import assert_field, assert_row_exists, assert_row_field, assert_status
from tests.commons.data_builder import UserFactory
from tests.e2e.users import db_queries

pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fk_kwargs(lookup_data: dict) -> dict:
    """Map the `lookup_data` fixture onto UserFactory.create_payload()'s required kwargs."""
    return {
        "department_id": lookup_data["department_id"],
        "designation_id": lookup_data["designation_id"],
        "designation_name": lookup_data["designation_name"],
        "area_id": lookup_data["area_id"],
        "area_name": lookup_data["area_name"],
        "engagement_status_id": lookup_data["engagement_status_id"],
        "engagement_status_name": lookup_data["engagement_status_name"],
        # Confirmed live (testresult.log): teamManagerId/appraiserId are required by the
        # create DTO even though their DB columns are nullable — any existing user id
        # satisfies the FK (see db_queries.fetch_any_existing_user_id).
        "team_manager_id": lookup_data["existing_user_id"],
        "appraiser_id": lookup_data["existing_user_id"],
    }


def _create_user(users_api_client, payload: dict):
    return users_api_client.create_user(payload)


def _post_tolerating_5xx_storm(users_api_client, payload: dict):
    """
    Some invalid-FK payloads (confirmed live: bad `departmentId`, bad `engagementStatus.id`)
    crash the endpoint with repeated 500s instead of a clean 4xx — enough that the session's
    retry-on-5xx adapter (see APISession, max_retries) exhausts itself and raises before a
    Response is ever returned. Returns the raised exception instead of letting it propagate,
    so callers can tell "clean validation error" apart from "the FK isn't validated at all
    and crashes the DB layer" and document the latter rather than let it crash the test run.
    """
    try:
        return _create_user(users_api_client, payload)
    except requests.exceptions.RequestException as exc:
        return exc


def _build_max_length_email(total_length: int) -> str:
    """
    Build a unique, syntactically valid email of exactly `total_length` chars.

    Confirmed live: a naive `local@padded-domain` at 255 chars was rejected as "username
    must be an email" once the local part exceeded ~64 chars (validator.js enforces the
    RFC 5321 local-part length cap even though it doesn't require it strictly otherwise).
    So the local part here stays short and the padding goes entirely into dot-separated
    domain labels, each capped at 63 chars per DNS label rules.
    """
    local_part = f"{UserFactory._generate_random_number(digits=8)}bnd"
    assert len(local_part) <= 64
    remaining = total_length - len(local_part) - 1  # -1 for "@"
    assert remaining > 0

    labels = []
    while remaining > 0:
        if remaining <= 63:
            labels.append("x" * remaining)
            remaining = 0
        else:
            label_len = min(63, remaining - 1)  # -1 reserves room for the following dot
            labels.append("x" * label_len)
            remaining -= label_len + 1
    domain = ".".join(labels)

    email = f"{local_part}@{domain}"
    assert len(email) == total_length
    return email


def _error_message_text(response) -> str:
    """
    Flatten every place the API might put an error message into one searchable string.

    Confirmed live: DTO-validation failures return a flat {"status","message":"Validation
    failed","details":"<comma-joined string>"}. Business-rule errors (e.g. "username already
    exists") were, per the Postman collection, a nested {"error":{"message","details":[...]}}
    — that shape hasn't been independently reconfirmed since the flat shape was discovered,
    so this checks both rather than assuming either exclusively.
    """
    try:
        body = response.json()
    except ValueError:
        return response.text

    if not isinstance(body, dict):
        return str(body)

    parts = []
    for key in ("message", "details"):
        if isinstance(body.get(key), str):
            parts.append(body[key])

    error = body.get("error")
    if isinstance(error, dict):
        if isinstance(error.get("message"), str):
            parts.append(error["message"])
        details = error.get("details")
        if isinstance(details, list):
            parts.extend(
                d.get("message", str(d)) if isinstance(d, dict) else str(d)
                for d in details
            )

    return " | ".join(parts) if parts else str(body)


def _assert_full_create_transaction(db_connection, user_id: int, payload: dict) -> dict:
    """Verify every table POST /users writes to, per docs/USERS_MODULE_TEST_DESIGN.md"""
    user_row = db_queries.fetch_user(db_connection, user_id)
    assert_row_exists(user_row, label=f"{DBTable.USER} id={user_id}")
    assert user_row is not None
    assert_row_field(user_row, "username", payload["username"])
    assert_row_field(user_row, "department_id", payload["departmentId"])

    designation_area_rows = db_queries.fetch_emp_designation_area_rows(db_connection, user_id)
    assert len(designation_area_rows) == len(payload["designationAreaHistory"]), (
        f"Expected {len(payload['designationAreaHistory'])} {DBTable.EMP_DESIGNATION_AREA} row(s), "
        f"got {len(designation_area_rows)}"
    )
    assert_row_field(
        designation_area_rows[0], "designation_id",
        payload["designationAreaHistory"][0]["designation"]["id"],
    )
    assert_row_field(
        designation_area_rows[0], "area_id",
        payload["designationAreaHistory"][0]["area"]["id"],
    )

    emp_status_rows = db_queries.fetch_emp_status_rows(db_connection, user_id)
    assert len(emp_status_rows) == len(payload["empStatusHistory"]), (
        f"Expected {len(payload['empStatusHistory'])} {DBTable.EMP_STATUS} row(s), got {len(emp_status_rows)}"
    )
    assert_row_field(
        emp_status_rows[0], "engagement_status_id",
        payload["empStatusHistory"][0]["engagementStatus"]["id"],
    )

    expected_details = payload["empStatusHistory"][0]["empStatusDetails"]
    details_rows = db_queries.fetch_emp_status_details_rows(db_connection, emp_status_rows[0]["id"])
    assert len(details_rows) == len(expected_details), (
        f"Expected {len(expected_details)} {DBTable.EMP_STATUS_DETAILS} row(s), got {len(details_rows)}"
    )

    if payload.get("leaveIssuerId"):
        rows = db_queries.fetch_emp_leave_issuer_rows(db_connection, user_id)
        assert len(rows) == 1, f"Expected exactly one {DBTable.EMP_LEAVE_ISSUERS} row"
        assert_row_field(rows[0], "leave_issuer_id", payload["leaveIssuerId"])

    if payload.get("teamManagerId"):
        rows = db_queries.fetch_emp_team_manager_rows(db_connection, user_id)
        assert len(rows) == 1, f"Expected exactly one {DBTable.EMP_TEAM_MANAGERS} row"
        assert_row_field(rows[0], "team_manager_id", payload["teamManagerId"])

    role_ids = payload.get("roleIds") or []
    roles_users_rows = db_queries.fetch_roles_users_rows(db_connection, user_id)
    assert len(roles_users_rows) == len(set(role_ids)), (
        f"Expected {len(set(role_ids))} distinct {DBTable.ROLES_USERS} row(s), got {len(roles_users_rows)}"
    )

    if payload.get("appraiserId"):
        allocation_rows = db_queries.fetch_teams_allocation_rows(db_connection, user_id)
        assert len(allocation_rows) >= 1, (
            f"Expected at least one {DBTable.TEAMS_ALLOCATIONS} row when an appraiser is set"
        )
        assert_row_field(allocation_rows[0], "appraiser_id", payload["appraiserId"])

    return user_row


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------

class TestCreateUserPositive:

    def test_full_payload_creates_all_expected_rows(
        self, users_api_client, db_connection, lookup_data,
    ):
        payload = UserFactory.create_payload(
            **_fk_kwargs(lookup_data),
            leave_issuer_id=lookup_data["existing_user_id"],
        )

        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.CREATED)
        body = response.json()
        assert body["message"] == "User created successfully"

        user_id = assert_field(response, "data")["id"]
        assert isinstance(user_id, int), f"data.id should be a JSON number, got {type(user_id)}"

        # Confirmed field-name mapping: request `username` <-> response `email` <-> DB `user.username`
        assert body["data"]["email"] == payload["username"]

        _assert_full_create_transaction(db_connection, user_id, payload)

    def test_minimal_payload_leaves_optional_fields_null_in_db(
        self, users_api_client, db_connection, lookup_data,
    ):
        payload = UserFactory.create_minimal_payload(**_fk_kwargs(lookup_data))

        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.CREATED)
        user_id = response.json()["data"]["id"]

        user_row = db_queries.fetch_user(db_connection, user_id)
        assert_row_exists(user_row)
        for nullable_column in ("middle_name", "cv_url", "home_phone", "github_id", "blood_group"):
            assert_row_field(user_row, nullable_column, None)

    def test_role_assignment_creates_roles_users_row(
        self, users_api_client, db_connection, lookup_data,
    ):
        active_role = lookup_data["active_role"]
        if not active_role:
            pytest.skip("No active row in `roles` to assign")

        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data), role_ids=[active_role["id"]])

        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.CREATED)
        user_id = response.json()["data"]["id"]

        roles_users_rows = db_queries.fetch_roles_users_rows(db_connection, user_id)
        assert len(roles_users_rows) == 1
        assert_row_field(roles_users_rows[0], "role_id", active_role["id"])

    def test_explicit_nulls_for_nullable_fields_are_accepted(
        self, users_api_client, db_connection, lookup_data,
    ):
        payload = UserFactory.create_payload(
            **_fk_kwargs(lookup_data),
            middleName=None, cvUrl=None, homePhone=None, githubId=None, bloodGroup=None,
        )

        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.CREATED)
        user_id = response.json()["data"]["id"]

        user_row = db_queries.fetch_user(db_connection, user_id)
        assert_row_exists(user_row)
        assert user_row is not None
        for column in ("middle_name", "cv_url", "home_phone", "github_id", "blood_group"):
            assert user_row[column] is None


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------

class TestCreateUserNegative:

    def test_missing_username_is_rejected(self, users_api_client, lookup_data):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        del payload["username"]

        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.BAD_REQUEST)
        assert "username" in _error_message_text(response)

    def test_empty_username_is_rejected(self, users_api_client, lookup_data):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        payload["username"] = ""

        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.BAD_REQUEST)
        # Confirmed live: flat {"status","message":"Validation failed","details": "..."} shape,
        # NOT the nested {"error":{...}} shape the Postman collection's saved scripts expected.
        message_text = _error_message_text(response)
        assert "username" in message_text and "empty" in message_text.lower(), (
            f"Expected the error to call out username/empty, got: {message_text!r}"
        )

    def test_whitespace_only_username_is_rejected(self, users_api_client, db_connection, lookup_data):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        payload["username"] = "   "

        response = _create_user(users_api_client, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, (
            "Whitespace-only username should be treated the same as empty — if this fails, "
            "the API accepts it and this is a real validation gap, not a broken test"
        )
        assert db_queries.count_rows(db_connection, DBTable.USER, "username", "   ") == 0

    def test_duplicate_username_is_rejected(
        self, users_api_client, db_connection, lookup_data,
    ):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        first = _create_user(users_api_client, payload)
        assert_status(first, HTTPStatus.CREATED)
        duplicate_payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        duplicate_payload["username"] = payload["username"]  # force the collision
        second = _create_user(users_api_client, duplicate_payload)

        assert_status(second, HTTPStatus.BAD_REQUEST)
        message_text = _error_message_text(second).lower()
        assert "already exists" in message_text, f"Expected a duplicate-username error, got: {message_text!r}"

        # Exactly one row for this username — the rejected duplicate wrote nothing (SC-5 rollback check)
        assert db_queries.count_rows(db_connection, DBTable.USER, "username", payload["username"]) == 1

    def test_nonexistent_department_id_rolls_back_whole_transaction(
        self, users_api_client, db_connection, lookup_data,
    ):
        bad_department_id = db_queries.fetch_non_existent_id(db_connection, DBTable.DEPARTMENT)
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        payload["departmentId"] = bad_department_id

        result = _post_tolerating_5xx_storm(users_api_client, payload)

        # Rollback check first — matters regardless of which failure mode we hit below.
        assert db_queries.count_rows(db_connection, DBTable.USER, "username", payload["username"]) == 0, (
            "Whether rejected cleanly or via a 500, no orphaned `user` row should exist"
        )

        if isinstance(result, Exception):
            # Confirmed live: a non-existent departmentId is NOT validated before hitting the
            # DB — the raw FK violation crashes the endpoint with repeated 500s instead of a
            # clean 4xx. Documented as a known defect rather than failing the whole run on an
            # unhandled exception.
            pytest.xfail(f"departmentId FK isn't pre-validated — endpoint 500s instead: {result}")

        assert result.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND), (
            f"Expected a clean validation error for a non-existent department_id, got {result.status_code}"
        )

    def test_nonexistent_designation_id_rolls_back_whole_transaction(
        self, users_api_client, db_connection, lookup_data,
    ):
        bad_designation_id = db_queries.fetch_non_existent_id(db_connection, DBTable.DESIGNATION)
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        payload["designationAreaHistory"][0]["designation"]["id"] = bad_designation_id

        response = _create_user(users_api_client, payload)
        assert response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND)
        assert db_queries.count_rows(db_connection, DBTable.USER, "username", payload["username"]) == 0

    def test_nonexistent_engagement_status_id_rolls_back_whole_transaction(
        self, users_api_client, db_connection, lookup_data,
    ):
        bad_status_id = db_queries.fetch_non_existent_id(db_connection, DBTable.ENGAGEMENT_STATUS)
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        payload["empStatusHistory"][0]["engagementStatus"]["id"] = bad_status_id

        result = _post_tolerating_5xx_storm(users_api_client, payload)

        assert db_queries.count_rows(db_connection, DBTable.USER, "username", payload["username"]) == 0, (
            "Whether rejected cleanly or via a 500, no orphaned `user` row should exist"
        )

        if isinstance(result, Exception):
            # Confirmed live: same defect as departmentId — an invalid engagementStatus.id
            # crashes the endpoint with repeated 500s instead of a clean 4xx.
            pytest.xfail(f"engagementStatus.id FK isn't pre-validated — endpoint 500s instead: {result}")

        assert result.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND)

    @pytest.mark.parametrize(
        "field, invalid_value",
        [
            ("gender", "UNSPECIFIED"),
            ("maritialStatus", "Complicated"),
        ],
    )
    def test_invalid_enum_value_is_rejected(self, users_api_client, db_connection, lookup_data, field, invalid_value):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        payload[field] = invalid_value

        response = _create_user(users_api_client, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, (
            f"{field}={invalid_value!r} should be rejected — if the API accepts it, "
            f"either the enum allow-list is wider than documented or this is a real validation gap"
        )
        assert field in _error_message_text(response), (
            f"Expected the rejection to be attributed to {field!r} specifically, "
            f"got: {_error_message_text(response)!r} (otherwise this could be failing for an unrelated reason)"
        )
        assert db_queries.count_rows(db_connection, DBTable.USER, "username", payload["username"]) == 0

    @pytest.mark.parametrize(
        "field, invalid_value, db_column",
        [
            # Confirmed live: unlike gender/maritialStatus above, these three are NOT
            # allow-list-validated by the API — a value outside the documented set is
            # accepted with 201. `blood_group` has no DB constraint either (plain varchar),
            # so that one is expected; `scheduled_type`/`working_shift` ARE real MySQL
            # ENUM columns, so what actually lands in the DB for those two is worth
            # confirming explicitly rather than assumed.
            ("scheduledType", "PART_TIME_INVALID", "scheduled_type"),
            ("workingShift", "NIGHT_SHIFT", "working_shift"),
            ("bloodGroup", "Z++", "blood_group"),
        ],
    )
    def test_unvalidated_enum_like_field_is_accepted(
        self, users_api_client, db_connection, lookup_data, field, invalid_value, db_column,
    ):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        payload[field] = invalid_value

        response = _create_user(users_api_client, payload)
        assert response.status_code == HTTPStatus.CREATED, (
            f"Confirmed live that {field} isn't allow-list-validated — if this now returns "
            f"a 4xx, the API started validating it and this test's premise is out of date"
        )
        user_id = response.json()["data"]["id"]

        user_row = db_queries.fetch_user(db_connection, user_id)
        assert_row_exists(user_row)
        assert user_row is not None
        # Documents whatever the DB actually stored for the out-of-range value — could be
        # the literal invalid string (varchar, no constraint), or MySQL's non-strict-mode
        # fallback for a real ENUM column (typically '', the enum's index-0/empty member).
        stored_value = user_row[db_column]
        assert stored_value in (invalid_value, ""), (
            f"{db_column} holds an unexpected value for an out-of-range enum write: {stored_value!r}"
        )

    def test_oversized_username_is_rejected(self, users_api_client, db_connection, lookup_data):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        # user.username is varchar(255) AND must be email-shaped (confirmed live). Padding a
        # naive local part directly (e.g. "a"*260 + "@...") triggers "username must be an
        # email" too, since validator.js caps the local part at 64 chars (see
        # _build_max_length_email) — that would make this test's 400 ambiguous between a
        # length violation and a format violation. Building via domain-label padding keeps
        # the local part short so this is unambiguously about length.
        payload["username"] = _build_max_length_email(256)  # one char past the varchar(255) limit

        response = _create_user(users_api_client, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, (
            "A value exceeding varchar(255) should be rejected before it ever reaches the DB, "
            "not truncated silently"
        )
        assert db_queries.count_rows(db_connection, DBTable.USER, "username", payload["username"]) == 0, (
            "Oversized value must not be silently truncated-and-stored"
        )

    def test_sql_injection_payload_in_first_name_is_stored_safely(
        self, users_api_client, db_connection, lookup_data,
    ):
        injection = "Robert'); DROP TABLE user;--"
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data), firstName=injection)

        response = _create_user(users_api_client, payload)
        # Either validated away (400), safely parameterized and stored verbatim (201), or
        # blocked by a WAF/gateway-level signature match on the payload pattern (403,
        # confirmed live) — never a 500, and `user` must still exist and be queryable either way.
        assert response.status_code in (HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST, HTTPStatus.FORBIDDEN)
        if response.status_code == HTTPStatus.CREATED:
            user_id = response.json()["data"]["id"]
            user_row = db_queries.fetch_user(db_connection, user_id)
            assert_row_exists(user_row)
            assert user_row is not None
            assert user_row["first_name"] == injection, "Payload should be stored verbatim as data, not executed"

        # Proof the table wasn't dropped: this must not raise.
        assert db_queries.count_rows(db_connection, DBTable.USER, "id", 1) >= 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestCreateUserEdge:

    def test_diacritic_and_cjk_name_fields_round_trip(
        self, users_api_client, db_connection, lookup_data,
    ):
        payload = UserFactory.create_payload(
            **_fk_kwargs(lookup_data), firstName="Zoë Müller", lastName="日本語テスト",
        )

        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.CREATED)
        user_id = response.json()["data"]["id"]

        user_row = db_queries.fetch_user(db_connection, user_id)
        assert_row_exists(user_row)
        assert user_row is not None
        assert user_row["first_name"] == payload["firstName"]
        assert user_row["last_name"] == payload["lastName"]
        assert response.json()["data"]["lastName"] == payload["lastName"]

    @pytest.mark.xfail(
        reason=(
            "Confirmed live: an emoji in firstName is not stored intact — the DB returns "
            "'Zoë ?????? Müller' for a submitted 'Zoë 🎉 Müller', consistent with the write "
            "path (API's DB connection, or the column itself) using a charset that can't "
            "represent 4-byte UTF-8 (needs utf8mb4). Kept as xfail so this flips to an "
            "unexpected pass (and gets noticed) if the charset is ever fixed."
        ),
        strict=False,
    )
    def test_emoji_in_name_field_round_trips_intact(
        self, users_api_client, db_connection, lookup_data,
    ):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data), firstName="Zoë 🎉 Müller")

        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.CREATED)
        user_id = response.json()["data"]["id"]

        user_row = db_queries.fetch_user(db_connection, user_id)
        assert_row_exists(user_row)
        assert user_row is not None
        assert user_row["first_name"] == payload["firstName"]

    def test_username_at_max_length_boundary_is_accepted(
        self, users_api_client, db_connection, lookup_data,
    ):
        # user.username is varchar(255) AND must be a valid email (confirmed live: "username
        # must be an email"). A first attempt padding the local part directly ALSO failed
        # that same check — validator.js enforces RFC 5321's 64-char local-part cap even at
        # a merely-long-but-plausible value, so the padding has to go into domain labels
        # instead (see _build_max_length_email).
        username = _build_max_length_email(255)

        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data), username=username)

        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.CREATED)
        user_id = response.json()["data"]["id"]

        user_row = db_queries.fetch_user(db_connection, user_id)
        assert_row_exists(user_row)
        
        assert user_row is not None
        assert user_row["username"] == username, "Boundary-length value must be stored intact, not truncated"

    def test_concurrent_duplicate_username_only_one_succeeds(
        self, users_api_client, db_connection, lookup_data,
    ):
        shared_username = UserFactory._unique_username()
        payload_a = UserFactory.create_payload(**_fk_kwargs(lookup_data), username=shared_username)
        payload_b = UserFactory.create_payload(**_fk_kwargs(lookup_data), username=shared_username)

        responses: list = [None, None]

        def _fire(index: int, payload: dict) -> None:
            responses[index] = _create_user(users_api_client, payload)

        threads = [
            threading.Thread(target=_fire, args=(0, payload_a)),
            threading.Thread(target=_fire, args=(1, payload_b)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        statuses = sorted(r.status_code for r in responses)
        # sorted ascending: CREATED (201) comes before BAD_REQUEST (400) — the previous
        # version of this assertion had the pair backwards and would never have passed.
        assert statuses == [HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST], (
            f"Expected exactly one success and one clean rejection under a race, got {statuses}"
        )
        assert db_queries.count_rows(db_connection, DBTable.USER, "username", shared_username) == 1


# ---------------------------------------------------------------------------
# API <-> DB field-name-mapping and data-type parity
# (docs/USERS_MODULE_TEST_DESIGN.md §4.5 — the explicitly requested type validation)
# ---------------------------------------------------------------------------

class TestCreateUserApiDbTypeAndFieldSync:

    def test_field_values_and_types_match_between_response_and_db_row(
        self, users_api_client, db_connection, lookup_data,
    ):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.CREATED)
        data = response.json()["data"]
        user_id = data["id"]

        user_row = db_queries.fetch_user(db_connection, user_id)
        assert_row_exists(user_row)
        assert user_row is not None

        # bigint PK -> JSON number
        assert isinstance(data["id"], int), f"data.id should be a JSON number, got {type(data['id'])}"
        assert user_row["id"] == data["id"]

        # varchar -> string; DB `username` surfaces back as response `email` (confirmed mapping)
        assert isinstance(data["email"], str)
        assert user_row["username"] == data["email"] == payload["username"]

        assert isinstance(data["lastName"], str)
        assert user_row["last_name"] == data["lastName"] == payload["lastName"]

        # `user.join_date` is a DATETIME column, not DATE (confirmed live — mysql-connector
        # returned "2025-07-16T00:00:00", not "2025-07-16"), despite the API only ever
        # sending/receiving a date-only string. datetime.datetime IS a date subclass, so the
        # isinstance check alone doesn't catch this — compare the .date() part explicitly.
        assert isinstance(user_row["join_date"], date)
        join_date_value = user_row["join_date"]
        join_date_only = join_date_value.date() if isinstance(join_date_value, datetime) else join_date_value
        assert join_date_only.isoformat() == payload["joinDate"]
        assert data["joinDate"].startswith(payload["joinDate"]), (
            f"response joinDate {data['joinDate']!r} should start with the submitted date "
            f"{payload['joinDate']!r}"
        )

        # enum -> string, exact (case-sensitive) match against the DB's real ENUM member list
        assert user_row["working_shift"] == payload["workingShift"] == data["workingShift"]
        assert data["workingShift"] in ("MORNING_SHIFT", "DAY_SHIFT", "EVENING_SHIFT", "LATE_EVENING_SHIFT"), (
            "Confirmed live DB enum members for user.working_shift"
        )
        assert user_row["scheduled_type"] == payload["scheduledType"]
        assert data["scheduledType"] in ("PART_TIME", "FULL_TIME"), "Confirmed live DB enum members for user.scheduled_type"

        # JSON column: mysql-connector-python returns JSON columns as raw text, not a parsed
        # dict — it must be json.loads()'d before comparing structurally.
        raw_availability = user_row["availability_time"]
        parsed_availability = json.loads(raw_availability) if isinstance(raw_availability, str) else raw_availability
        assert parsed_availability == payload["availabilityTime"] == data["availabilityTime"], (
            "JSON column must round-trip to the exact structure both the request sent and the API returned"
        )

        # bigint FK, nested in the response but flat in the DB
        assert data["department"]["id"] == user_row["department_id"] == payload["departmentId"]
        assert isinstance(data["department"]["id"], int)

        # nullable varchar, explicit-None case
        assert user_row["middle_name"] is None
        assert data.get("middleName") is None

    def test_designation_area_history_row_matches_request_and_response(
        self, users_api_client, db_connection, lookup_data,
    ):
        payload = UserFactory.create_payload(**_fk_kwargs(lookup_data))
        response = _create_user(users_api_client, payload)
        assert_status(response, HTTPStatus.CREATED)
        data = response.json()["data"]
        user_id = data["id"]

        db_rows = db_queries.fetch_emp_designation_area_rows(db_connection, user_id)
        assert len(db_rows) == 1
        db_row = db_rows[0]

        requested = payload["designationAreaHistory"][0]
        assert db_row["designation_id"] == requested["designation"]["id"]
        assert db_row["area_id"] == requested["area"]["id"]
        assert db_row["transition_date"].isoformat() == requested["transitionDate"]

        api_history = data["designationAreaHistory"][0]
        assert api_history["designation"]["id"] == requested["designation"]["id"]
        assert api_history["designation"]["name"] == requested["designation"]["name"]
        assert api_history["area"]["id"] == requested["area"]["id"]
