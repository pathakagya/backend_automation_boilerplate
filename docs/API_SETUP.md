# API Setup

> **Onboarding step 3 of 7** | Prev: [ENV_CONFIG.md](ENV_CONFIG.md) | Next: [DATABASE_SETUP.md](DATABASE_SETUP.md)

---

## How APISession works

`APISession` (in `src/core/api_session_manager.py`) wraps `requests.Session` and adds:

- Auth injection per request (bearer, basic, API key, or custom headers)
- Base URL prepending so tests use relative paths (`/users`, not `https://...`)
- Configurable timeouts and retry logic
- Automatic Allure attachment of request/response details

Tests receive `api_session` as a fixture — they never instantiate `APISession` directly.

---

## Auth strategies

Set `API_AUTH_TYPE` in your `.env.dev` file and supply the matching credentials.

### `none` — no authentication

```ini
API_AUTH_TYPE=none
API_BASE_URL=https://api.example.com
```

Use this for public APIs or when your tests handle auth themselves.

---

### `bearer` — Authorization: Bearer token

```ini
API_AUTH_TYPE=bearer
API_TOKEN=your_token
```

The token is injected on every request as `Authorization: Bearer <token>`.

---

### `basic` — HTTP Basic Auth

```ini
API_AUTH_TYPE=basic
API_USERNAME=testuser
API_PASSWORD=secret
```

Credentials are base64-encoded and injected as `Authorization: Basic <encoded>`.

---

### `api_key` — Custom header

```ini
API_AUTH_TYPE=api_key
API_KEY=abc123xyz
API_KEY_HEADER=X-API-Key      # header name (default: X-API-Key)
```

The key is injected as a request header: `X-API-Key: abc123xyz`.

---

### `api_key_param` — Query string parameter

```ini
API_AUTH_TYPE=api_key_param
API_KEY=abc123xyz
```

The key is appended as a query param: `GET /users?api_key=abc123xyz`.

---

### `custom_headers` — Arbitrary headers

Inject any set of static headers on every request. Configure in `tests/conftest.py` directly:

```python
from core.api_session_manager import APISession

session = APISession(
    base_url="https://api.example.com",
    auth_type="custom_headers",
    custom_headers={
        "X-Tenant-Id": "acme",
        "X-Client-Version": "2.0",
    },
    timeout=30,
    attach_allure=True,
)
```

---

## Primary API session (default)

The `api_session` fixture is session-scoped and automatically built from your config. You do not need to create it — just inject it into your test:

```python
def test_list_users(api_session):
    response = api_session.get("/users")
    assert response.status_code == 200
```

`api_session` reads from `API_BASE_URL`, `API_AUTH_TYPE`, and the matching credential vars automatically via `tests/conftest.py` → `SharedTestResources.get_primary_api_session()`.

---

## Multi-service setup

When your project talks to more than one service (e.g., a main API and an auth service), create additional session fixtures in `tests/conftest.py`.

### Option A — Use the built-in auth service session

If you only need a second service for auth, set `AUTH_SERVICE_BASE_URL` and use the built-in fixture:

```ini
AUTH_SERVICE_BASE_URL=https://auth.example.com
```

```python
def test_token_refresh(auth_service_session):
    response = auth_service_session.post("/auth/refresh", json={"token": "..."})
    assert response.status_code == 200
```

`auth_service_session` is already wired in `tests/conftest.py` — no code changes needed.

### Option B — Add a fully configured extra session

Use `make_api_fixture` from `src/fixtures/api_fixtures.py` to create additional named sessions:

```python
# tests/conftest.py
from fixtures.api_fixtures import make_api_fixture

# Reads from config section "billing_api" → env vars BILLING_API_BASE_URL, BILLING_API_AUTH_TYPE, etc.
billing_session = make_api_fixture("billing_api")
notifications_session = make_api_fixture("notifications_api")
```

Then add matching env vars:

```ini
BILLING_API_BASE_URL=https://billing.example.com
BILLING_API_AUTH_TYPE=bearer
BILLING_API_TOKEN=eyJ...

NOTIFICATIONS_API_BASE_URL=https://notify.example.com
NOTIFICATIONS_API_AUTH_TYPE=api_key
NOTIFICATIONS_API_KEY=notif-key-123
```

---

## Using api_session in tests

```python
from helpers.assertions import assert_status, assert_field, assert_list_not_empty

def test_get_user(api_session):
    response = api_session.get("/users/42")
    assert_status(response, 200)
    assert_field(response, "id", 42)
    assert_field(response, "email")          # just checks key exists

def test_create_user(api_session):
    payload = {"name": "Alice", "email": "alice@example.com"}
    response = api_session.post("/users", json=payload)
    assert_status(response, 201)
    user_id = assert_field(response, "id")   # returns the value
    return user_id

def test_list_users(api_session):
    response = api_session.get("/users")
    assert_status(response, 200)
    assert_list_not_empty(response, "data")  # checks response.json()["data"] is non-empty list
```

### Using `request_and_assert` (convenience wrapper)

```python
from helpers.api_helper import request_and_assert

def test_get_user(api_session):
    # Performs the request and asserts status in one call
    response = request_and_assert(api_session, "GET", "/users/42", expected_status=200)
```

---

## Dynamic token auth (authenticate at runtime)

If the token must be fetched at test time (e.g., login before each test run):

```python
from helpers.api_helper import authenticate_and_set_token

def test_with_fresh_token(api_session):
    authenticate_and_set_token(
        session=api_session,
        login_endpoint="/auth/login",
        credentials={"username": "admin", "password": "pass"},
        token_key="access_token",     # JSON key in login response
    )
    response = api_session.get("/protected-resource")
    assert response.status_code == 200
```

---

## Timeout and retry configuration

Override defaults in your `.env.dev`:

```ini
API_TIMEOUT=60          # seconds per request (default: 30)
```

Or configure per session in code:

```python
from core.api_session_manager import APISession

session = APISession(
    base_url="https://slow-api.example.com",
    auth_type="bearer",
    token="...",
    timeout=120,
    attach_allure=True,
)
```

---

## Common pitfalls

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `401 Unauthorized` on every request | Wrong `API_AUTH_TYPE` or expired token | Check `API_AUTH_TYPE` matches the API expectation; refresh `API_TOKEN` |
| `ConnectionError` | Wrong `API_BASE_URL` (trailing slash, wrong scheme) | Confirm the URL is reachable: `curl $API_BASE_URL/health` |
| `KeyError: 'base_url'` in fixture | `API_BASE_URL` not set | Export `API_BASE_URL` or add to `.env.dev` |
| Tests pass locally but fail in CI | Token or URL not set as CI secret | Add all required vars to GitHub Secrets |

---

## Next step

→ [DATABASE_SETUP.md](DATABASE_SETUP.md) — configure the database connection for integration and e2e tests
