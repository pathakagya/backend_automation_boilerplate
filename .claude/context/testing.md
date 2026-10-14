# Testing conventions

## Markers

Registered in `pytest.ini` and `src/conftest.py`:

| Marker | Use |
|--------|-----|
| `smoke` | Critical-path subset; run before full suite |
| `integration` | API vs DB **count parity** on GET endpoints and master tables (read-only) |
| `e2e` | Feature **CRUD** flows; may use data factories and `state` |
| `db_required` | Tests that require a project-owned DB adapter to be configured; skipped gracefully when `DB_ENGINE` is not set |
| `rbac` | Role-based access control tests; uses `make_role_fixture` and per-role credentials from env |

Constants: `src/core/constants.py` → `Marker.INTEGRATION`, `Marker.E2E`, `Marker.SMOKE`, `Marker.DB_REQUIRED`, `Marker.RBAC`

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

**Must:** `@pytest.mark.integration`, live API + DB, `tests.commons.assertions` + `helpers.db_helper`.

**Must not:** CRUD, `BaseFactory`/factory `.create_payload()` calls, `state` fixture.

```text
tests/integration/
├── conftest.py
├── test_<resource>_counts.py
└── ...
```

### `tests/e2e/` — feature CRUD and workflows

**Purpose:** **Create → Read → Update → Delete** (or product lifecycle) via API, with DB checks where needed.

**Must:** `@pytest.mark.e2e`, `tests/e2e/<feature>/`, a `tests/commons/data_builder/<feature>.py` factory for payloads, `state` for multi-step IDs.

**Must not:** Count-parity-only tests (use integration).

```text
tests/e2e/<feature>/
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

- **Generic base class (ships with the boilerplate):** `src/helpers/data_builders.py` —
  `BaseFactory` (`create_payload()`/`create_many()`) plus random generators re-exported from
  `helpers.common` (`random_string`, `random_int`, `random_email`, `unique_id`).
- **Project extension point:** `tests/commons/data_builder/shared.py` — `ProjectBaseFactory`
  (extends `BaseFactory`). Extend `ProjectBaseFactory`, not `BaseFactory` directly, for feature
  factories.
- **Feature factories:** `tests/commons/data_builder/<feature>.py` — one file per feature, all
  re-exported from `tests/commons/data_builder/__init__.py`.
- **Use:** **only** in `tests/e2e/` for create/update payloads; never in smoke or integration.

```
tests/commons/data_builder/
├── __init__.py            ← re-exports every factory class
├── shared.py               ← ProjectBaseFactory (extend this)
├── user_factory.py         ← UserFactory (real, kept reference — see tests/e2e/users/)
└── <feature>.py            ← add one per feature
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

- `make_api_fixture(section, scope)` — extra API sessions (different services)
- `make_db_fixture(ConnectionClass, section, scope)` — extra DB connections
- `make_role_fixture(role_name, scope, login_path, token_key)` — per-role authenticated session for RBAC tests; reads `{ROLE}_API_USERNAME` / `{ROLE}_API_PASSWORD`, skips gracefully when not configured — see `docs/RBAC_TESTING.md`

### Fixtures by tier

| Tier | Use |
|------|-----|
| Smoke | `api_session`, optional `db_connection` |
| Integration | `api_session`, `db_connection` |
| E2E | `api_session`, `db_connection`, **`state`** |

## Helpers

Import boilerplate-layer helpers as `helpers.<module>` (`pythonpath = src`); import assertions
and factories from `tests.commons.*` (see `.claude/rules/assertions.md` /
`.claude/rules/testing.md` for why the two layers are split).

| Module | Use for |
|--------|---------|
| `tests.commons.assertions` | See `assertions.md` — import ALL assertions from here, not `helpers.assertions` |
| `helpers.api_helper` | `authenticate_and_set_token`, `paginate_all` |
| `helpers.db_helper` | `fetch_row`, `insert_row`, `temp_row`, `compare_dicts` |
| `helpers.data_builders` | `BaseFactory` (generic base only) |
| `tests.commons.data_builder` | `ProjectBaseFactory` + every feature factory (e.g. `UserFactory`) — **e2e only** |
| `helpers.polling` | `wait_until` |

| Tier | Primary helpers |
|------|-----------------|
| Smoke | `assert_response_status`, `assert_response_time`, `SmokeModule` |
| Integration | `assert_row_count`, `assert_list_not_empty`, `fetch_row`, `paginate_all` |
| E2E | typed API client, `tests.commons.data_builder` factories, `temp_row`, `state`, `assert_row_field` |

```python
# api_helper
all_items = paginate_all(api_session, "/users", items_key="data", next_key="next")

# db_helper
row = fetch_row(db_connection, "users", {"email": "x@y.com"}, schema="app_schema")
```

## Stateful E2E

- Persist IDs on `state`; reuse across steps; `state.snapshot()` for Allure.

## Assertions

Full API: `.claude/context/assertions.md` → `tests/commons/assertions.py` (generic primitives
underneath in `src/helpers/assertions.py`).

## Pytest defaults (`pytest.ini`)

- Allure: `--alluredir=allure-results --clean-alluredir`
- Parallel: `--dist=loadscope`
- Timeout: 120s (`timeout_method = thread`)

## Running tiers

| Tier | Command |
|------|---------|
| Smoke | `pytest tests/smoke -m smoke -ra` |
| Integration | `pytest tests/integration -m integration -ra` |
| E2E | `pytest tests/e2e -m e2e -ra` |
| All | `pytest tests/smoke -m smoke -ra && pytest tests/integration -m integration -ra && pytest tests/e2e -m e2e -ra` |

Boilerplate today: `tests/smoke/` has tests; add `tests/integration/` and `tests/e2e/<feature>/` per project.
