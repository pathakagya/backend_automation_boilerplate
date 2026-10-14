# Architecture

## Goals

- Reuse one boilerplate across multiple projects
- Keep core generic and driver-agnostic
- Make setup and extension explicit for humans and AI tools

---

## Layers

| # | Layer | Location | Responsibility |
|---|-------|----------|----------------|
| 1 | Configuration | `src/core/config_manager.py` | Loads `.env.{ENV}`, INI, YAML; env vars always win |
| 2 | Core runtime | `src/core/` | API session, DB abstraction, state, constants, auth client |
| 3 | Typed API clients | `api/` | `BaseAPIClient` subclasses — one per feature area |
| 4 | Fixtures & helpers | `src/fixtures/`, `src/helpers/` | Fixture factories, assertions, DB ops, data builders |
| 5 | Project-facing commons | `tests/commons/` | Composed assertions, feature factories, response schemas |
| 6 | Tests | `tests/` | Smoke / integration / e2e suites consuming the layers above |

### Layer 1 — Configuration

`ConfigManager` resolves values from shell env vars → `.env.{ENV}` file → `.ini` → `.yaml` (shell always wins). Returns plain `dict` — no Pydantic, no ORM. `ENV` selects which env file loads; `src/conftest.py` instantiates it session-wide.

### Layer 2 — Core runtime (`src/core/`)

| Module | Purpose |
|--------|---------|
| `api_session_manager.py` | Wraps `requests.Session`; auth strategies: `none / bearer / basic / api_key / api_key_param / custom_headers`; retry, timeout, Allure request/response attachment on every call |
| `db_connection_manager.py` | Abstract `DatabaseConnection` base; `paramstyle`-aware (qmark/numeric/named/format/pyformat); `connect / disconnect / execute / fetch_one / fetch_all / transaction()` context manager; zero driver imports |
| `auth_client.py` | Dedicated `APISession` for `AUTH_SERVICE_BASE_URL` — use when auth is a separate service |
| `state_manager.py` + `state_extensions.py` | Function-scoped key/value store (`StateManager`); `snapshot()` attaches state to Allure; `state_extensions` adds `ContextualState` and `TypedStateManager` for advanced patterns |
| `test_resources.py` | `SharedTestResources` / `TestResourcesManager` — session-scoped API + DB lifecycle; `DB_ENGINE_MAP = {"mysql": MysqlConnection, "postgresql": PostgreSQLConnection, "oracle": OracleConnection}`; selects adapter from `DB_ENGINE` env var or `DB_ADAPTER_CLASS` override |
| `constants.py` | `APIPath`, `DBTable`, `DBSchema`, `SmokeModule`, `SmokeTimeoutSeconds`, `SmokeExpectedStatus`, `Marker` (SMOKE / INTEGRATION / E2E / DB_REQUIRED / RBAC), `SmokeDefaults` |

### Layer 3 — Typed API clients (`api/`)

`BaseAPIClient` (`api/base_client.py`) wraps an injected `APISession` and provides:

```
get / post / put / patch / delete
get_path(path_template, path_params)     — "{id}"-style substitution
get_with_path(path, *segments)           — appended segments
url_for(path_template, **path_params)    — full URL for paginators
```

One subclass per feature module (e.g. `api/users_client.py`). Tests never call `api_session` directly for feature endpoints — they always inject the typed client fixture.

### Layer 4 — Fixtures & helpers

**Fixture factories (`src/fixtures/`):**

| Factory | Use |
|---------|-----|
| `make_api_fixture(section, scope)` | Extra named `APISession` for a secondary service |
| `make_db_fixture(ConnectionClass, section, scope)` | Extra DB connection from a config section |
| `make_role_fixture(role_name, scope, login_path, token_key)` | Per-role authenticated session for RBAC tests |

**Helpers (`src/helpers/`):**

| Module | Key symbols |
|--------|-------------|
| `assertions.py` | `assert_status`, `assert_response_status`, `assert_response_time`, `assert_field`, `assert_list_not_empty`, `assert_row_exists`, `assert_row_count`, `assert_row_field` |
| `api_helper.py` | `authenticate_and_set_token`, `paginate_all` |
| `db_helper.py` | `fetch_row`, `insert_row`, `temp_row` (auto-cleanup via yield), `compare_dicts` |
| `db_operations.py` | `row_count`, `fetch_rows_by_field`, `bulk_insert`, `bulk_temp_rows`, `delete_where`, `update_row` |
| `data_builders.py` | `BaseFactory.create_payload()`, `create_many()`; random generators |
| `common.py` | `random_string`, `random_int`, `random_email`, `unique_id` |
| `polling.py` | `wait_until(fn, timeout_seconds, description)` — for eventual-consistency assertions |

### Layer 5 — Project-facing commons (`tests/commons/`)

| Path | Purpose |
|------|---------|
| `assertions.py` | Re-exports all generic helpers + composed: `assert_api_db_sync`, `assert_response_schema`. **Always import from here** — never from `src/helpers/assertions.py` directly |
| `data_builder/` | `ProjectBaseFactory` (`shared.py`), one factory file per feature, `__init__.py` re-exports all. Produce plain dicts — no ORM, no DB writes. Used only in e2e |
| `api_schemas/` | Response shape dicts for `assert_response_schema`, one file per module |

### Layer 6 — Tests (`tests/`)

| Tier | Folder | Marker | Purpose |
|------|--------|--------|---------|
| Smoke | `tests/smoke/` | `@pytest.mark.smoke` | Health & connectivity — no CRUD, no DB required |
| Integration | `tests/integration/` | `@pytest.mark.integration` | API list count vs DB count (read-only, no factories) |
| E2E | `tests/e2e/<feature>/` | `@pytest.mark.e2e` | Full CRUD workflows with `state` fixture and typed client |
| RBAC | any tier | `@pytest.mark.rbac` | Role-based access — uses `make_role_fixture` sessions |

---

## Fixture hierarchy

```
conftest.py (repo root)          ← re-exports src/conftest for pytest discovery
src/conftest.py                  ← session: ConfigManager, SharedTestResources, run_prefix, state
tests/conftest.py                ← PROJECT WIRING: api_session, db_connection, auth_service_session
tests/<tier>/conftest.py         ← optional tier-wide fixtures
tests/e2e/<feature>/conftest.py  ← feature fixtures: <feature>_api_client, RBAC sessions
```

Override project fixtures in `tests/conftest.py` only. Never modify `src/conftest.py` for project-specific logic.

---

## Data flow

```
ConfigManager
  └── APISession  ─────────────────────────────────┐
  └── DatabaseConnection (via DB_ENGINE_MAP)        │
          └── SharedTestResources (tests/conftest.py)
                  └── fixtures: api_session, db_connection, state, run_prefix
                          ├── typed API client  (api/<feature>_client.py)
                          ├── data factory      (tests/commons/data_builder/<feature>.py)
                          └── tests             (smoke / integration / e2e)
                                  ├── assertions (tests/commons/assertions.py)
                                  └── Allure report (allure-results/ → GitHub Pages via CI)
```

---

## Design decisions

- **Core purity**: no DB driver imports in `src/core/` — drivers live in `src/project/db/` only
- **Typed API clients**: `BaseAPIClient` subclasses isolate URL construction from test code
- **DB placeholder syntax**: engine-resolved via `conn.paramstyle` — never hardcode `%s` or `:1` in tests or helpers
- **Config as plain dicts**: `ConfigManager` returns `dict`, no ORM or Pydantic dependency
- **Teardown is explicit**: fixtures use `yield`; `temp_row` auto-deletes via context manager
- **Parallel execution**: pytest-xdist (`--dist=loadscope`); `run_prefix` prevents data collisions across workers
- **Async DB writes**: `helpers.polling.wait_until` instead of `time.sleep()`
- **Allure integration**: `APISession` attaches request/response automatically; wrap test steps with `allure.step()` manually; `src/conftest.py` writes `allure-results/environment.properties` and copies `config/allure_categories.json` at session start
- **RBAC**: `make_role_fixture` reads `{ROLE}_API_USERNAME` / `{ROLE}_API_PASSWORD` from env; skips gracefully when not configured

---

## How to adapt for a project

The minimal set of files to touch — nothing else should need to change:

| File | What to do |
|------|-----------|
| `config/.env.dev` | Fill in `API_BASE_URL`, `API_AUTH_TYPE`, DB engine and credentials |
| `tests/conftest.py` | Wire `api_session` and `db_connection` fixtures for your project |
| `src/core/constants.py` | Add `APIPath` endpoint paths and `DBTable` table/column name constants |
| `src/project/db/<engine>_connection.py` | Only if your DB engine isn't MySQL, PostgreSQL, or Oracle |

> **Engine selection**: set `DB_ENGINE=mysql|postgresql|oracle` in config. `TestResourcesManager.DB_ENGINE_MAP` dynamically imports the right adapter — no fixture override needed. For a fully custom adapter, set `DB_ADAPTER_CLASS` to the fully qualified class path instead.

**Reference implementation**: `tests/e2e/users/` is a real, kept reference (study the patterns, don't copy-paste it as a template for a new module).

**Scaffolding**: the `setup-test-module` skill automates creating the API client, factory, conftest, and test file for a new feature module — see `.claude/skills/setup-test-module/SKILL.md`.

---

## Supporting files

| File / Dir | Purpose |
|------------|---------|
| `scripts/generate_email_report.py` | Reads `allure-results/` JSON; renders `email_body.html` via Jinja2 for CI email |
| `scripts/email_template.html` | Jinja2 HTML email template — edit freely for team branding |
| `config/allure_categories.json` | Allure failure categorisation — auto-copied to results dir at session start |
| `.github/workflows/test.yml` | CI: api-smoke → db-tests → publish-report → notify |
| `CLAUDE.md` / `AGENTS.md` | AI assistant entry points — imports all `.claude/context/` files |
