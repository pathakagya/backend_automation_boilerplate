# Test Patterns

> **Onboarding step 5 of 7** | Prev: [DATABASE_SETUP.md](DATABASE_SETUP.md) | Next: [EXTENDING.md](EXTENDING.md)

---

## The three test tiers

Every test in this project belongs to exactly one tier. The tier determines the folder, the marker, and what the test is allowed to do.

| Tier | Folder | Marker | Purpose | Uses factories? | Uses `state`? |
|------|--------|--------|---------|-----------------|---------------|
| Smoke | `tests/smoke/` | `@pytest.mark.smoke` | Health, contracts, and optional connectivity | No | No |
| Integration | `tests/integration/` | `@pytest.mark.integration` + optional `db_required` | API list count vs DB count | No | No |
| E2E | `tests/e2e/<feature>/` | `@pytest.mark.e2e` + optional `db_required` | Full CRUD/workflows | Yes | Yes |

Run order: **smoke first** — if smoke fails, there is no point running integration or e2e.

```bash
pytest tests/smoke -m "smoke and not db_required" -ra # fast API-only smoke
pytest tests/integration -m integration -ra        # requires DB
pytest tests/e2e -m e2e -ra                        # requires DB

# All three in order
pytest tests/smoke -m smoke -ra && pytest tests/integration -m integration -ra && pytest tests/e2e -m e2e -ra
```

---

## Pattern 1 — Smoke test

**Purpose:** Verify that the API is reachable and responds within acceptable time. No CRUD.
DB connectivity is a separate `db_required` smoke check.

**Folder:** `tests/smoke/`

**What to test:**
- Health endpoints (`/health`, `/status`)
- Required env vars are present
- DB is reachable (connectivity only, no data assertions) when the DB preset is selected
- OpenAPI spec is accessible

**Template:**

```python
# tests/smoke/test_api_health.py
import pytest
import allure
from core.constants import SmokeModule
from tests.commons.assertions import assert_response_status, assert_response_time

@pytest.mark.smoke
class TestAPIHealth:

    @allure.title("Health endpoint returns 200 within threshold")
    def test_health_endpoint(self, api_session):
        with allure.step("GET /health"):
            response = api_session.get("/health")

        with allure.step("Assert status and response time"):
            assert_response_status(response, SmokeModule.HEALTH)
            assert_response_time(response, SmokeModule.HEALTH)

    @allure.title("OpenAPI spec is accessible")
    def test_openapi_spec(self, api_session):
        response = api_session.get("/openapi.json")
        assert_response_status(response, SmokeModule.GENERIC_GET)
```

**Assertion helpers for smoke:**

| Helper | Use |
|--------|-----|
| `assert_response_status(response, SmokeModule.X)` | Status matches the expected code for that module |
| `assert_response_time(response, SmokeModule.X)` | Elapsed time is under the threshold for that module |

Thresholds and expected statuses are defined in `src/core/constants.py` — update `SmokeTimeoutSeconds` and `SmokeExpectedStatus` for your project.

---

## Pattern 2 — Integration test (count parity)

**Purpose:** Assert that the number of records returned by the API list endpoint matches the count in the database. Read-only — no data creation, no factories.

**Folder:** `tests/integration/`

**What to test:**
- Every GET/list API endpoint where count parity matters
- Master/reference tables (roles, statuses, categories, etc.)

**Template:**

```python
# tests/integration/test_users_count.py
import pytest
import allure
from tests.commons.assertions import assert_row_count, assert_list_not_empty
from helpers.api_helper import paginate_all
from helpers.db_helper import fetch_row

@pytest.mark.integration
@pytest.mark.db_required
class TestUsersCount:

    @allure.title("API user count matches DB count")
    def test_user_count_parity(self, api_session, db_connection):
        with allure.step("Fetch all users from API"):
            # paginate_all collects all pages for you
            api_items = paginate_all(
                api_session,
                "/users",
                items_key="data",     # key in response JSON that holds the list
                next_key="next",      # pagination cursor key (or None for total-based)
            )

        with allure.step("Count rows in DB"):
            row = db_connection.fetch_one("SELECT COUNT(*) AS total FROM users")
            db_count = row["total"]

        with allure.step("Compare counts"):
            assert len(api_items) == db_count, (
                f"API returned {len(api_items)} users, DB has {db_count}"
            )
```

**Simpler form — when the API returns `total` in the response body:**

```python
@pytest.mark.integration
def test_user_count_parity_via_total(self, api_session, db_connection):
    response = api_session.get("/users?per_page=1")
    assert response.status_code == 200

    api_total = response.json()["total"]

    row = db_connection.fetch_one("SELECT COUNT(*) AS cnt FROM users")
    db_total = row["cnt"]

    assert api_total == db_total, f"API total={api_total}, DB total={db_total}"
```

**Rules for integration tests:**
- No `BaseFactory`, no factory `.create_payload()` calls
- No `state` fixture
- No CRUD (POST/PUT/DELETE)
- Use `assert_list_not_empty` to confirm the endpoint returns data at all

---

## Pattern 3 — E2E test (CRUD workflow)

**Purpose:** Simulate a real user journey: create a resource via API, read it back, update it, delete it. Verify DB state at each step.

**Folder:** `tests/e2e/<feature>/`

### Step A — Create the factory

```python
# tests/commons/data_builder/accounts.py
from helpers.common import random_email, random_string
from tests.commons.data_builder.shared import ProjectBaseFactory

class AccountFactory(ProjectBaseFactory):
    @classmethod
    def create_payload(cls, **overrides):
        payload = {
            "name": f"account_{random_string(6)}",
            "email": random_email(),
            "role": "viewer",
        }
        payload.update(overrides)
        return payload

class AdminAccountFactory(AccountFactory):
    @classmethod
    def create_payload(cls, **overrides):
        return super().create_payload(role="admin", **overrides)
```

Register both in `tests/commons/data_builder/__init__.py`'s re-exports. (This example uses
`AccountFactory` rather than `UserFactory` to avoid colliding with the real, kept
`UserFactory` in `tests/commons/data_builder/user_factory.py` — see `tests/e2e/users/`.)

### Step B — Write the test

```python
# tests/e2e/accounts/test_account_crud.py
import pytest
import allure
from tests.commons.assertions import assert_status, assert_field, assert_row_exists, assert_row_field
from helpers.db_helper import fetch_row
from tests.commons.data_builder import AccountFactory

@pytest.mark.e2e
class TestAccountCRUD:

    @allure.title("Account lifecycle: create → read → update → delete")
    def test_account_crud(self, api_session, db_connection, state, run_prefix):
        payload = AccountFactory.create_payload(name=f"{run_prefix}_alice")

        # --- CREATE ---
        with allure.step("POST /accounts — create account"):
            response = api_session.post("/accounts", json=payload)
            assert_status(response, 201)
            account_id = assert_field(response, "id")
            state.set("account_id", account_id)       # persist for downstream steps

        # --- DB CHECK after create ---
        with allure.step("Assert account exists in DB"):
            row = fetch_row(db_connection, "accounts", {"id": account_id}, schema="app_schema")
            assert_row_exists(row, label="account after create")
            assert_row_field(row, "email", payload["email"])

        # --- READ ---
        with allure.step("GET /accounts/{id} — read back"):
            response = api_session.get(f"/accounts/{account_id}")
            assert_status(response, 200)
            assert_field(response, "name", payload["name"])

        # --- UPDATE ---
        with allure.step("PUT /accounts/{id} — update name"):
            update_payload = {"name": f"{run_prefix}_alice_updated"}
            response = api_session.put(f"/accounts/{account_id}", json=update_payload)
            assert_status(response, 200)

        # --- DB CHECK after update ---
        with allure.step("Assert updated name in DB"):
            row = fetch_row(db_connection, "accounts", {"id": account_id}, schema="app_schema")
            assert_row_field(row, "name", update_payload["name"])

        # --- DELETE ---
        with allure.step("DELETE /accounts/{id}"):
            response = api_session.delete(f"/accounts/{account_id}")
            assert_status(response, 204)

        # --- DB CHECK after delete ---
        with allure.step("Assert account removed from DB"):
            row = fetch_row(db_connection, "accounts", {"id": account_id}, schema="app_schema")
            assert row is None, f"Expected account {account_id} to be deleted, but found row: {row}"
```

---

## The `state` fixture

`state` is a function-scoped `StateManager`. Use it to pass IDs and tokens between steps within a single test.

```python
# Save a value
state.set("user_id", 42)
state.set("token", "abc123")

# Read it back later in the same test
user_id = state.get("user_id")

# Attach all state to Allure for traceability
state.snapshot()   # call at the end of the test or in a step
```

`state` is **automatically cleared** after each test. Never use it to share data between test functions.

---

## The `run_prefix` fixture

`run_prefix` is a session-scoped unique string (e.g. `run_gw0_a3f7c2b1`). Use it to namespace test data so parallel runs don't collide:

```python
payload = AccountFactory.create_payload(name=f"{run_prefix}_alice")
```

This ensures that even if two test sessions run simultaneously against the same DB, their data is distinguishable.

---

## Data builders — rules

| Rule | Why |
|------|-----|
| Factories live in `tests/commons/data_builder/<feature>.py` | One shared location for every factory, regardless of which tier uses it |
| Factories extend `ProjectBaseFactory` (not `BaseFactory` directly) | `ProjectBaseFactory` is the project-wide extension point; `BaseFactory` (`helpers/data_builders.py`) ships generic with the boilerplate |
| Factories implement `create_payload(cls, **overrides)` | The override pattern — build defaults, then `payload.update(overrides)` |
| Factories produce plain dicts only | No ORM, no DB writes in factories |
| Never use factories in smoke or integration tests | Those tiers are read-only |

---

## Fixture layering

```
src/conftest.py              ← session scope: config, run_prefix, state
tests/conftest.py            ← session scope: api_session, db_connection, auth_service_session
tests/e2e/conftest.py        ← optional: e2e-wide fixtures
tests/e2e/<feature>/conftest.py  ← optional: feature-specific fixtures
```

Override `api_session` or `db_connection` in `tests/conftest.py` only. Never modify `src/conftest.py` for project-specific logic.

---

## Next step

→ [EXTENDING.md](EXTENDING.md) — add a new feature folder, factory, and test from scratch
