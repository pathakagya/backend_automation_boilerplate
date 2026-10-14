# API Setup

> **Onboarding step 3 of 7** | Prev: [ENV_CONFIG.md](ENV_CONFIG.md) | Next: [DATABASE_SETUP.md](DATABASE_SETUP.md)

---

## The API layer at a glance

Four files own the API stack. Each has exactly one job — read this section once and the rest
of this doc is just detail.

```
config/.env.dev  (API_BASE_URL, API_AUTH_TYPE, ...)
        │
        ▼
ConfigManager.get_api_config()                      ← src/core/config_manager.py
        │
        ▼
APISession                                          ← src/core/api_session_manager.py
        │   raw HTTP transport: auth injection, base_url, timeout, retries, Allure attachment
        │   built ONCE per test session by tests/conftest.py's `api_session` fixture
        ▼
BaseAPIClient                                        ← api/base_client.py
        │   wraps an existing APISession, adds "{param}" path templating — no transport logic
        ▼
<Feature>Client (e.g. UsersClient)                   ← api/<feature>_client.py
        │   one method per business action: create_user(), get_user_roles(), ...
        ▼
Tests                                                ← tests/smoke|integration|e2e/
```

Two more modules operate *across* this stack rather than sitting in the chain:

| Module | Role |
|--------|------|
| `src/helpers/api_helper.py` | Free functions that take any `APISession` (or a client's `.session`) — request+assert in one call, pagination, one-shot login |
| `src/fixtures/api_fixtures.py` | Optional fixture factory for **extra** sessions (a second service) or pre-authenticated role sessions — not where your default `api_session` comes from |

---

## File-by-file reference

| File | What it is | Owns |
|------|-----------|------|
| `src/core/api_session_manager.py` | `APISession` class | Auth injection, base URL resolution, timeout, retry adapter, Allure request/response attachment. The only place that talks to `requests` directly. |
| `api/base_client.py` | `BaseAPIClient` class | Thin organizing layer over an *existing* `APISession` — path-parameter substitution, appended segments, URL resolution. Adds zero transport logic of its own. |
| `api/<feature>_client.py` | e.g. `UsersClient(BaseAPIClient)` | One typed client per feature module — business-named methods (`create_user`, not `post_user`). This is what tests actually call. See `api/users_client.py` for the real, worked example. |
| `src/helpers/api_helper.py` | `authenticate_and_set_token`, `paginate_all` | One-shot login, cursor-pagination collection. |
| `src/fixtures/api_fixtures.py` | `make_api_fixture`, `auth_client`, `role_api_session` | Opt-in pytest fixtures for a **second** service or a **pre-authenticated** session. Must be explicitly imported into `tests/conftest.py` to activate. |
| `core/auth_client.py` | `AuthClient` class | Stateful login + token caching + refresh. Used internally by `api_fixtures.py`'s `auth_client`/`role_api_session`. |

---

## Where your `api_session` fixture actually comes from

There are **two** `api_session` fixture definitions in this codebase — don't confuse them:

- **`tests/conftest.py`** (session-scoped, backed by `TestResourcesManager`) — this is the one
  your tests actually receive. It's built once per test run from `config.get_api_config()`.
- **`src/fixtures/api_fixtures.py`** has its own example `api_session` fixture (function-scoped)
  with the same name. It is **not registered anywhere** unless a project explicitly imports it —
  it exists only as a documented pattern. Pulling in `make_api_fixture`, `auth_client`, or
  `role_api_session` from that module does not activate its `api_session` too.

If you ever see two different-looking `api_session` definitions while reading the source, this
is why — the real one always wins because `tests/conftest.py` is closer to your tests in
pytest's fixture resolution order.

---

## Auth strategies

Set `API_AUTH_TYPE` in your `.env.dev` file and supply the matching credentials.

### `none` — no authentication

```ini
API_AUTH_TYPE=none
API_BASE_URL=https://api.example.com
```

### `bearer` — Authorization: Bearer token

```ini
API_AUTH_TYPE=bearer
API_TOKEN=your_token
```

Injected on every request as `Authorization: Bearer <token>`.

### `basic` — HTTP Basic Auth

```ini
API_AUTH_TYPE=basic
API_USERNAME=testuser
API_PASSWORD=secret
```

### `api_key` — Custom header

```ini
API_AUTH_TYPE=api_key
API_KEY=abc123xyz
API_KEY_HEADER=X-API-Key      # header name (default: X-API-Key)
```

Injected as a request header: `X-API-Key: abc123xyz`.

### `api_key_param` — Query string parameter

```ini
API_AUTH_TYPE=api_key_param
API_KEY=abc123xyz
API_KEY_PARAM_NAME=api_key    # query param name (default: api_key)
```

Appended as a query param on every request through the session: `GET /users?api_key=abc123xyz`.

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

## Writing a typed API client (the required pattern)

**Every** endpoint call for a feature module must go through a typed client extending
`BaseAPIClient` — never `api_session.get/post/put(...)` with a raw path called directly from a
test. See `.claude/rules/api-standards.md` for the full rule and `api/users_client.py` for a
real, worked reference.

```python
# api/orders_client.py
from api.base_client import BaseAPIClient
from core.constants import APIPath

class OrdersClient(BaseAPIClient):
    def create_order(self, payload, **kwargs):
        return self.post(APIPath.ORDERS, json=payload, **kwargs)

    def get_order(self, order_id, **kwargs):
        return self.get_path(APIPath.ORDER_BY_ID, {"id": order_id}, **kwargs)   # "{id}" substitution

    def get_order_notes(self, order_id, **kwargs):
        return self.get_with_path(APIPath.ORDER_NOTES, order_id, "notes", **kwargs)  # appended segments
```

`BaseAPIClient` never builds its own `APISession` — it always wraps the one your test already
has, so auth, retries, and Allure attachment stay consistent. Endpoint paths always come from
`core.constants.APIPath`, never a hardcoded string — see `.claude/rules/api-standards.md`.

To scaffold a new client automatically, use the `generate-api-client` skill
(`.claude/skills/generate-api-client/SKILL.md`).

---

## Wiring the client fixture and using it in a test

Add a `<module>_api_client` fixture in that module's own `conftest.py` — never in the global
`tests/conftest.py`:

```python
# tests/e2e/orders/conftest.py
import pytest
from api.orders_client import OrdersClient
from core.api_session_manager import APISession

@pytest.fixture
def orders_api_client(api_session: APISession) -> OrdersClient:
    return OrdersClient(api_session)
```

Then use it in the test — never `api_session` directly:

```python
# tests/e2e/orders/test_order_crud.py
from tests.commons.assertions import assert_status, assert_field

def test_create_order(orders_api_client, state):
    response = orders_api_client.create_order({"customer_name": "Alice", "product_id": 1})
    assert_status(response, 201)
    state.set("order_id", assert_field(response, "id"))
```

---

## `api_helper.py` — request helpers

Free functions that take an `APISession` (or `<client>.session`, the escape hatch every
`BaseAPIClient` exposes) as their first argument.

### `paginate_all` — follow cursor/page pagination and collect every item

```python
from helpers.api_helper import paginate_all

all_users = paginate_all(api_session, "/users", items_key="data", next_key="next")
```

Stops when `next_key` is missing/falsy in the response, or after `max_pages` (default 50, a
safety limit against infinite-loop pagination bugs). If the `next` value is a full URL it's
followed directly; otherwise it's sent as a `cursor` query param.

### `authenticate_and_set_token` — one-shot login

```python
from helpers.api_helper import authenticate_and_set_token

token = authenticate_and_set_token(
    session=api_session,
    login_path="/auth/login",
    credentials={"username": "admin", "password": "pass"},
)
```

POSTs credentials, extracts the token from the response (via
`helpers.response_parser.extract_token`, which checks `token`/`access_token`/`accessToken` at
the response root and under a `data` key), and calls `session.set_bearer_token(token)`. No
caching or refresh — it re-authenticates every time it's called. For a cached, auto-refreshing
token, use `AuthClient` (below) instead.

---

## Advanced: cached/refreshing auth with `AuthClient`

`core/auth_client.py::AuthClient` wraps an `APISession` and adds what
`authenticate_and_set_token` deliberately doesn't: it caches the token, checks expiry, and
transparently refreshes before falling back to a full re-login.

```python
from core.auth_client import AuthClient

auth = AuthClient(session=api_session, login_path="/auth/token", refresh_path="/auth/refresh")
token = auth.get_valid_token(username="qa_user", password="qa_pass")
# subsequent calls reuse the cached token until it's within 30s of expiring, then refresh
```

`src/fixtures/api_fixtures.py` already wires this into two opt-in fixtures — import them into
your `tests/conftest.py` to use:

```python
# tests/conftest.py
from fixtures.api_fixtures import auth_client, role_api_session  # noqa: F401  (re-exported as fixtures)
```

| Fixture | Scope | Behavior |
|---------|-------|----------|
| `auth_client` | session | An `AuthClient` built from your primary `api_session` config — inject it to call `get_valid_token()` yourself. |
| `role_api_session` | function | A fresh `APISession` pre-authenticated via `auth_client`, using `API_ROLE_USERNAME`/`API_ROLE_PASSWORD` (read through `config.get("api", "role_username")`). Use for role-based scenarios (e.g. "as an approver, ..."). |

Set the role credentials as real environment variables (exported in the shell, or CI secrets —
see the note on env-var visibility below):

```ini
API_ROLE_USERNAME=approver_user
API_ROLE_PASSWORD=approver_pass
```

---

## Second services / multi-API setup

### Option A — the built-in auth service session

If you only need a second service for auth, set `AUTH_SERVICE_BASE_URL` and use the fixture
that's already wired in `tests/conftest.py`:

```ini
AUTH_SERVICE_BASE_URL=https://auth.example.com
```

```python
def test_token_refresh(auth_service_session):
    response = auth_service_session.post("/auth/refresh", json={"token": "..."})
    assert response.status_code == 200
```

### Option B — a fully configured extra session

Use `make_api_fixture` from `src/fixtures/api_fixtures.py` for any additional named service:

```python
# tests/conftest.py
from fixtures.api_fixtures import make_api_fixture

# Reads BILLING_API_BASE_URL, BILLING_API_AUTH_TYPE, BILLING_API_TOKEN, ...
billing_session = make_api_fixture("billing_api")
notifications_session = make_api_fixture("notifications_api")
```

```ini
BILLING_API_BASE_URL=https://billing.example.com
BILLING_API_AUTH_TYPE=bearer
BILLING_API_TOKEN=eyJ...
```

`make_api_fixture(section)` calls `config.get_api_config(section)`, which reads
`{SECTION}_BASE_URL`, `{SECTION}_AUTH_TYPE`, etc. for any section name other than the default
`"api"`.

> **Env-var visibility note:** named-section variables (`BILLING_API_*`, `AUTH_SERVICE_BASE_URL`,
> `API_ROLE_USERNAME`) are read directly from the process environment. `ConfigManager` loads your
> chosen `.env.{ENV}` file with `python-dotenv` on startup (without overriding real shell/CI
> values — same override precedence as everything else in this framework), so adding them to
> `config/.env.dev` is enough locally. In CI, set them as real secrets/env vars on the job, same
> as any other `*_BASE_URL`/`*_TOKEN` variable.

---

## Using a client's `.session` escape hatch

Two legitimate cases for reaching past a typed client to its underlying session (see
`.claude/rules/api-standards.md` for the full list):

```python
# Pagination link-following — reuse the same authenticated session, never build a second one
next_page = orders_api_client.session.get(next_link_from_response_body)

# A path genuinely not in APIPath yet — add it to constants.py first; only fall back here
# if it truly can't be a named constant
response = orders_api_client.session.get("/some/undocumented/path")
```

---

## Timeout and retry configuration

Override defaults in your `.env.dev`:

```ini
API_TIMEOUT=60          # seconds per request (default: 30)
API_MAX_RETRIES=2       # retries on 500/502/503/504 (default: 2)
API_RETRY_BACKOFF=0.3   # exponential backoff factor
API_RETRY_UNSAFE_METHODS=false # only enable for idempotent write endpoints
```

Or configure per session in code:

```python
from core.api_session_manager import APISession

session = APISession(
    base_url="https://slow-api.example.com",
    auth_type="bearer",
    token="...",
    timeout=120,
    max_retries=3,
    retry_unsafe_methods=False,
    attach_allure=True,
)
```

Allure request/response attachments redact authorization headers, API keys,
passwords, and token-like fields before writing evidence.

---

## Common pitfalls

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `401 Unauthorized` on every request | Wrong `API_AUTH_TYPE` or expired token | Check `API_AUTH_TYPE` matches the API's expectation; refresh `API_TOKEN` |
| `ConnectionError` | Wrong `API_BASE_URL` (trailing slash, wrong scheme) | Confirm the URL is reachable: `curl $API_BASE_URL/health` |
| `KeyError: 'base_url'` in fixture | `API_BASE_URL` not set | Export `API_BASE_URL` or add to `.env.dev` |
| `make_api_fixture("billing_api")` hits the wrong service | `BILLING_API_*` vars not actually visible in the process env | Confirm they're in `config/.env.{ENV}` (loaded automatically) or exported in the shell/CI — see the env-var visibility note above |
| Editing `src/core/` to add a new endpoint client | New clients belong in `api/<feature>_client.py`, never `src/core/` | Extend `BaseAPIClient` in `api/`, keep `src/core/` driver/transport-agnostic |
| Test calls `api_session.get(...)` directly for a new module | Violates the typed-client rule | Write a client extending `BaseAPIClient` first — see "Writing a typed API client" above |
| Tests pass locally but fail in CI | Token or URL not set as CI secret | Add all required vars to GitHub Secrets |

---

## Next step

→ [DATABASE_SETUP.md](DATABASE_SETUP.md) — configure the database connection for integration and e2e tests
