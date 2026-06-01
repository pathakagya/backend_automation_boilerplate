# Testing conventions

## Markers

Registered in `pytest.ini` and `src/conftest.py`:

| Marker | Use |
|--------|-----|
| `smoke` | Critical-path subset; run before full suite |
| `integration` | API vs DB **count parity** on GET endpoints and master tables (read-only) |
| `e2e` | Feature **CRUD** flows; may use data factories and `state` |

Constants: `src/core/constants.py` → `Marker.INTEGRATION`, `Marker.E2E`, `Marker.SMOKE`

## Test suite layout (by folder)

Each tier has a fixed responsibility. Do not mix concerns across folders.

### `tests/smoke/`

- Fast health and connectivity checks (status, response time).
- No data factories; use `assert_response_status`, `assert_response_time`.

### `tests/integration/` — API vs DB count validation

**Purpose:** **GET/list data in the API matches the database** for read-only endpoints and master tables.

| What to test | How |
|--------------|-----|
| All **GET** endpoints (list/collection) | API count / `total` vs DB `COUNT(*)` |
| **Master tables** | `SmokeDefaults.DB_MASTER_TABLES` in `core.constants` |
| Single-resource GET | Optional: `assert_row_exists` after fetch by ID |

**Must:** `@pytest.mark.integration`, live API + DB, `helpers.assertions` + `helpers.db_helper`.

**Must not:** CRUD, `BaseFactory` / `*.build()`, `state` fixture.

```text
tests/integration/
├── conftest.py
├── test_<resource>_counts.py
└── ...
```

### `tests/e2e/` — feature CRUD and workflows

**Purpose:** **Create → Read → Update → Delete** (or product lifecycle) via API, with DB checks where needed.

**Must:** `@pytest.mark.e2e`, `tests/e2e/<feature>/`, `BaseFactory` for payloads, `state` for multi-step IDs.

**Must not:** Count-parity-only tests (use integration).

```text
tests/e2e/<feature>/
├── factories.py
├── conftest.py
└── test_<feature>_crud.py
```

## No unit tests in this repo

| Test type | Where |
|-----------|--------|
| Unit tests (mocked backend logic) | Backend **application** repo |
| Smoke / integration / e2e | **This repo** |

Do not add `tests/unit/` or a `unit` marker.

## Data factories (`BaseFactory`)

- **Base class:** `src/helpers/data_builders.py` — `BaseFactory`, `FakerFactory`, random generators
- **Feature factories:** `tests/e2e/data_builders/<feature>_factory.py` — one file per feature
- **Use:** **only** in `tests/e2e/` for create/update payloads; never in smoke or integration

```
tests/e2e/data_builders/
├── __init__.py
├── user_factory.py       ← UserFactory, AdminUserFactory, FakerUserFactory
└── <feature>_factory.py  ← add one per feature
```

## Fixtures

### Hierarchy

```text
conftest.py (repo root)           → re-exports src/conftest
src/conftest.py                   → config, state, markers, Allure
tests/conftest.py                 → api_session, db_connection — PROJECT WIRING
tests/integration|e2e/conftest.py → optional
tests/e2e/<feature>/conftest.py   → feature-specific
```

Override API/DB in **`tests/conftest.py`**, not `src/conftest.py`.

### `tests/conftest.py` (session)

| Fixture | Purpose |
|---------|---------|
| `shared_test_resources` | API sessions + DB lifecycle |
| `api_session` | Primary API client |
| `auth_service_session` | Optional `AUTH_SERVICE_BASE_URL` |
| `db_connection` | DB via engine map; missing config → `pytest.skip` |

### `src/conftest.py`

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `config` | session | `ConfigManager` |
| `run_prefix` | session | Isolated data prefix (parallel runs) |
| `state` | function | `StateManager` — **e2e only** |

### Optional factories (`src/fixtures/`)

- `make_api_fixture(section, scope)` — extra API sessions
- `make_db_fixture(ConnectionClass, section, scope)` — extra DB connections

### Fixtures by tier

| Tier | Use |
|------|-----|
| Smoke | `api_session`, optional `db_connection` |
| Integration | `api_session`, `db_connection` |
| E2E | `api_session`, `db_connection`, **`state`** |

## Helpers

Import: `helpers.<module>` (`pythonpath = src`).

| Module | Use for |
|--------|---------|
| `helpers.assertions` | See `assertions.md` |
| `helpers.api_helper` | `request_and_assert`, `authenticate_and_set_token`, `paginate_all` |
| `helpers.db_helper` | `fetch_row`, `insert_row`, `temp_row`, `compare_dicts` |
| `helpers.data_builders` | `BaseFactory`, `FakerFactory`, random generators (base only) |
| `tests.e2e.data_builders.<feature>_factory` | Feature-specific factories — **e2e only** |
| `helpers.polling` | `wait_until` |

| Tier | Primary helpers |
|------|-----------------|
| Smoke | `assert_response_status`, `assert_response_time`, `SmokeModule` |
| Integration | `assert_row_count`, `assert_list_not_empty`, `fetch_row`, `paginate_all` |
| E2E | `request_and_assert`, `BaseFactory`, `temp_row`, `state`, `assert_row_field` |

```python
# api_helper
response = request_and_assert(api_session, "GET", "/users", expected_status=200)
all_items = paginate_all(api_session, "/users", items_key="data", next_key="next")

# db_helper
row = fetch_row(db_connection, "users", {"email": "x@y.com"}, schema="app_schema")
```

## Stateful E2E

- Persist IDs on `state`; reuse across steps; `state.snapshot()` for Allure.

## Assertions

Full API: `.claude/context/assertions.md` → `src/helpers/assertions.py`.

## Pytest defaults (`pytest.ini`)

- Allure: `--alluredir=allure-results --clean-alluredir`
- Parallel: `--dist=loadscope`
- Timeout: 120s (`timeout_method = thread`)

## Running tiers

| Tier | Command |
|------|---------|
| Smoke | `make smoke` |
| Integration | `make integration` |
| E2E | `make e2e` |
| All | `make verify` |

Boilerplate today: `tests/smoke/` has tests; add `tests/integration/` and `tests/e2e/<feature>/` per project.
