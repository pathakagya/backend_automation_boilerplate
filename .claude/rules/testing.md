# Testing Rules

## Test tiers — do not mix concerns across folders

| Tier | Folder | Purpose | May use |
|------|--------|---------|---------|
| `smoke` | `tests/smoke/` | Fast health/connectivity checks | `assert_response_status`, `assert_response_time` — no factories |
| `integration` | `tests/integration/` | API vs DB **count parity** on GET/list endpoints and master tables (read-only) | `tests.commons.assertions`, `helpers.db_helper` — no `BaseFactory`, no `state` |
| `e2e` | `tests/e2e/<feature>/` | Feature CRUD / multi-step workflows | `ProjectBaseFactory` subclasses (`tests/commons/data_builder/`), `state`, typed API clients |

Full per-tier fixture/marker reference: `.claude/context/testing.md`. This file is the
enforceable Do/Don't rulebook.

## Fixtures

- Override project-specific API/DB fixtures in **`tests/conftest.py`**, never in
  `src/conftest.py` (that file is boilerplate-wide, shared across every fork of this template).
- One `conftest.py` per feature module for module-specific fixtures — never add
  feature-specific fixtures to the global `tests/conftest.py`.
- `state` (`StateManager`) is function-scoped and **e2e only** — never reach for it in
  smoke/integration tests.
- Perform assertions only in test files, not inside fixtures — a fixture that calls an API to
  set up preconditions may assert its own success (e.g. `assert_response_status` on a
  create-precondition call), but that isn't a substitute for the test's own assertions.

## Data factories

- Base classes: `tests/commons/data_builder/shared.py` — `BaseFactory` (generic) and
  `ProjectBaseFactory` (extend this one, not `BaseFactory` directly, for feature factories).
- One file per feature under `tests/commons/data_builder/<feature>.py` — this is the single
  location for **all** data builders, not just e2e ones; `tests/commons/data_builder/__init__.py`
  re-exports every factory class.
- All factory methods MUST accept `**kwargs`/explicit override params for field-level overrides
  — the pattern is "build a sensible default payload, then `payload.update(overrides)`", not
  branching logic per variant.
- Use `Faker` for dynamic/non-deterministic fields. IDs that must reference real DB rows (FKs)
  are always required, explicit kwargs — never Faker-generated. Audit fields (`created_by`,
  `modified_by`) are hardcoded to a project constant, not overridable via Faker.
- `BaseFactory`/`ProjectBaseFactory` produce plain dicts — no ORM, no DB writes.

## Test ordering (`pytest-order`)

Two legitimate ways to express a multi-step flow (create → approve → deny, create → read →
update → delete) — pick per case, don't default to the more complex one:

1. **One test method, sequential `allure.step()`s, `state` for cross-step data** — the default
   for most CRUD flows (see `docs/TEST_PATTERNS.md` Pattern 3). Simplest option; use it unless
   a real need forces the flow into separate test methods.
2. **Separate test methods + `@pytest.mark.order(N)`, `state` still carries IDs between them** —
   only when the steps genuinely need to be separate methods (e.g. distinct Allure
   pass/fail/retry granularity per step, or each step is independently useful to run/re-run).

```python
@pytest.mark.order(1)
def test_create_order(self, orders_api_client, state):
    response = orders_api_client.create_order(OrderFactory.create_payload())
    state.set("order_id", assert_field(response, "id"))

@pytest.mark.order(2)
def test_approve_order(self, orders_api_client, state):
    order_id = state.get("order_id")   # set by test_create_order, same class/file
    response = orders_api_client.approve_order(order_id)
    assert_status(response, 200)
```

- `pytest.ini` pins `--order-scope=module` — order numbers are compared within each module
  independently, not across the whole session. Don't omit this when invoking pytest directly for
  a subset of tests that rely on ordering (it's already baked into `addopts`, so plain `pytest
  <path>` picks it up automatically — only relevant if you're constructing a custom invocation
  that bypasses `addopts`).
- Ordered test methods MUST live in the same test class/file — `pytest.ini` pins
  `--dist=loadscope`, which keeps one class's tests on the same xdist worker; ordering across
  *different* classes or files is not guaranteed under parallel execution.
- `state` is function-scoped by default (`src/conftest.py`) — a fresh `StateManager` per test
  method, cleared after. That's correct for pattern 1 above (one method, one `StateManager`),
  but it means IDs set in `test_create_order` are **gone** by the time `test_approve_order`
  runs. For pattern 2 (separate ordered methods), override `state` with `scope="class"` in the
  module's own `conftest.py` so the same `StateManager` instance is shared across that class's
  ordered methods — don't touch the function-scoped default in `src/conftest.py` itself.

## Parallelism

- Tests run with `pytest-xdist`; `pytest.ini` pins `--dist=loadscope` — do not override this
  per-invocation without a specific reason.
- If a module's tests have an intra-file step order (single method or `@pytest.mark.order`),
  keep them in one file/class so `loadscope` scheduling keeps them on the same worker.
- Use `filelock` when reading/writing any shared file across workers.

## Async DB writes

Use `helpers.polling.wait_until` instead of `time.sleep()` — see `.claude/rules/assertions.md`.

## Setup Test Module Skill Rules

### Must follow
- **Naming**: module names in `snake_case`, classes in `PascalCase`, fixtures as
  `<module>_<resource>` (e.g. `orders_api_client`).
- **Imports**: absolute imports only (`pythonpath = src` is set in `pytest.ini`, so
  `from core.xyz import ...` / `from helpers.xyz import ...` — never relative imports, never a
  `src.` prefix).
- **API clients**: must extend `BaseAPIClient` (`api/base_client.py`).
- **Database names**: never hardcode table/column strings inline — pull from
  `src/core/constants.py` (add new constants there first if one is missing).
- **Generated code**: skill-generated files contain only essential setup — no template test
  methods, no commented-out examples. The user fills those in.
- **Fixtures**: a new module's `conftest.py` needs at minimum a `<module>_api_client` fixture;
  e2e modules also need module-specific `state`-consuming fixtures as needed.

### Must NOT do
- Include template methods or commented-out examples in generated files.
- Hardcode table/column/endpoint-path strings in tests.
- Use relative imports.
- Create an API client without the `BaseAPIClient` parent.
- Hardcode an endpoint path string directly in a test or fixture — use `APIPath` constants.
- Use `api_session` directly for a new module's endpoint calls instead of a typed client.
- Share `state` between modules — it is module-scoped by design.
