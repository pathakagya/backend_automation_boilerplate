# RBAC Testing Guide

Role-based access control (RBAC) testing verifies that your API enforces permissions correctly —
the right roles can do what they should, and the wrong roles are rejected.

This guide covers the three QA patterns and shows how to wire everything up in ~5 minutes.

---

## When to write RBAC tests

| Scenario | Test type |
|---|---|
| Endpoint must reject a role (e.g. `viewer` cannot `DELETE`) | Access control test — two fixtures, one endpoint |
| Multiple roles hit the same endpoint with different expected outcomes | Parametrized-by-role test |
| A workflow requires sequential actions by different actors (create → approve) | Multi-actor workflow test |

---

## 5-minute setup

### 1. Set credentials in `config/.env.dev`

```ini
# One block per role — any role name works
ADMIN_API_USERNAME=admin@example.com
ADMIN_API_PASSWORD=your-admin-password

VIEWER_API_USERNAME=viewer@example.com
VIEWER_API_PASSWORD=your-viewer-password
```

If your API has a separate auth service, also set:
```ini
AUTH_SERVICE_BASE_URL=https://auth.example.com
```

### 2. Register fixtures in `tests/conftest.py`

```python
from fixtures.api_fixtures import make_role_fixture

# One line per role — name becomes the fixture parameter name in tests
admin_session = make_role_fixture("admin")
viewer_session = make_role_fixture("viewer")
```

Or scope to a module if only one feature needs them:

```python
# tests/e2e/orders/conftest.py
from fixtures.api_fixtures import make_role_fixture

approver_session = make_role_fixture("approver")
```

### 3. Mark tests with `@pytest.mark.rbac`

```python
import pytest

@pytest.mark.rbac
@pytest.mark.e2e
class TestOrderPermissions:
    ...
```

---

## Pattern 1 — Access control

Two sessions, one endpoint, verify the 403.

```python
import pytest
from tests.commons.assertions import assert_status

@pytest.mark.rbac
@pytest.mark.e2e
class TestDeletePermission:
    def test_admin_can_delete_user(self, admin_session, state):
        user_id = state.get("user_id")   # set in a preceding create step
        response = admin_session.delete(f"/users/{user_id}")
        assert_status(response, 204)

    def test_viewer_cannot_delete_user(self, viewer_session, state):
        user_id = state.get("user_id")
        response = viewer_session.delete(f"/users/{user_id}")
        assert_status(response, 403)
```

---

## Pattern 2 — Parametrized by role

Same endpoint, different expected status per role. Useful for documenting a permission matrix.

```python
import pytest
from tests.commons.assertions import assert_status

@pytest.mark.rbac
@pytest.mark.e2e
class TestUserEndpointPermissions:
    @pytest.mark.parametrize("session_fixture,expected_status", [
        ("admin_session", 200),
        ("viewer_session", 403),
    ])
    def test_update_user_by_role(self, request, session_fixture, expected_status, state):
        session = request.getfixturevalue(session_fixture)
        response = session.patch(f"/users/{state.get('user_id')}", json={"name": "Updated"})
        assert_status(response, expected_status)
```

> `request.getfixturevalue(name)` is pytest's built-in way to resolve a fixture by name at
> runtime — no extra imports needed.

---

## Pattern 3 — Multi-actor workflow

Two sessions in one test; `state` carries the resource ID between actors.

```python
import pytest
import allure
from tests.commons.assertions import assert_status, assert_field

@pytest.mark.rbac
@pytest.mark.e2e
class TestApprovalWorkflow:
    def test_create_and_approve(self, creator_session, approver_session, state):
        with allure.step("Regular user submits a request"):
            payload = {"title": "Leave request", "days": 3}
            response = creator_session.post("/requests", json=payload)
            assert_status(response, 201)
            state.set("request_id", assert_field(response, "id"))

        with allure.step("Approver approves it"):
            request_id = state.get("request_id")
            response = approver_session.post(f"/requests/{request_id}/approve")
            assert_status(response, 200)

        with allure.step("Creator sees approved status"):
            response = creator_session.get(f"/requests/{request_id}")
            assert_field(response, "status", "approved")
```

---

## Running RBAC tests

```bash
# Only RBAC tests
pytest -m rbac -ra -s

# RBAC + e2e together
pytest -m "rbac and e2e" -ra

# Skip RBAC (when role creds not available)
pytest -m "not rbac" -ra
```

---

## Auto-skip when credentials are absent

`make_role_fixture` calls `pytest.skip(...)` when `{ROLE}_API_USERNAME` or
`{ROLE}_API_PASSWORD` is missing. You get a clear skip message instead of a failure:

```
SKIPPED tests/e2e/orders/test_permissions.py::TestDeletePermission::test_viewer_cannot_delete_user
  Role 'viewer' credentials not configured: VIEWER_API_USERNAME / VIEWER_API_PASSWORD
```

This means RBAC tests pass in CI without credentials (they skip cleanly) and only run fully
when the role secrets are supplied.

---

## CI — enabling RBAC tests

Add role credentials as GitHub secrets (Settings → Secrets and variables → Actions → Secrets):

| Secret | Value |
|---|---|
| `ADMIN_API_USERNAME` | Admin account email |
| `ADMIN_API_PASSWORD` | Admin account password |
| `VIEWER_API_USERNAME` | Viewer account email |
| `VIEWER_API_PASSWORD` | Viewer account password |

Then reference them in your workflow job's `env:` block:

```yaml
env:
  ADMIN_API_USERNAME: ${{ secrets.ADMIN_API_USERNAME }}
  ADMIN_API_PASSWORD: ${{ secrets.ADMIN_API_PASSWORD }}
  VIEWER_API_USERNAME: ${{ secrets.VIEWER_API_USERNAME }}
  VIEWER_API_PASSWORD: ${{ secrets.VIEWER_API_PASSWORD }}
```

---

## `make_role_fixture` reference

```python
from fixtures.api_fixtures import make_role_fixture

make_role_fixture(
    role_name,            # str — any name; drives env var prefix and fixture name
    scope="function",     # pytest scope (function/class/module/session)
    login_path="/auth/token",   # POST path used to exchange credentials for a token
    token_key="access_token",   # JSON key in the login response that holds the token
)
```

The returned fixture is a `Generator[APISession, None, None]` — use it exactly like
`api_session`.

---

## Env-var convention

| `role_name` | Env vars read |
|---|---|
| `"admin"` | `ADMIN_API_USERNAME`, `ADMIN_API_PASSWORD` |
| `"viewer"` | `VIEWER_API_USERNAME`, `VIEWER_API_PASSWORD` |
| `"approver"` | `APPROVER_API_USERNAME`, `APPROVER_API_PASSWORD` |
| any string | `{NAME.upper()}_API_USERNAME`, `{NAME.upper()}_API_PASSWORD` |

Full variable reference: [ENV_CONFIG.md](ENV_CONFIG.md#role-sessions-rbac)
