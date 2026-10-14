# Assertion helpers (`tests/commons/assertions.py`)

Use these helpers in tests instead of raw `assert` on test cases. Every
function raises **`AssertionError`** with a descriptive message (URL, body snippet, field names)
so pytest and Allure show clear failures.

Generic HTTP/DB primitives are defined once in `src/helpers/assertions.py` (ships with the
boilerplate, project-agnostic) and re-exported from `tests/commons/assertions.py`, which also
adds the project-facing composed assertions (`assert_api_db_sync`, `assert_response_schema`).
**Always import from `tests.commons.assertions`** — see `.claude/rules/assertions.md`.

## Import

```python
from tests.commons.assertions import (
    assert_response_status,
    assert_response_time,
    assert_field,
    assert_list_not_empty,
    assert_row_exists,
    assert_row_count,
    assert_row_field,
    assert_api_db_sync,
    assert_response_schema,
)
```

---

## HTTP / API assertions

| Function | Parameters | Asserts | On Failure | When to Use |
|---|---|---|---|---|
| `assert_status` | `response`, `expected` | `status_code == expected` | URL + body snippet | Exact status on any endpoint (e.g. `201` on create) |
| `assert_response_status` | `response`, `module_name` | Status matches `SmokeExpectedStatus` for module | Module name, expected vs actual, URL, body | Smoke tests where expected status varies by endpoint type |
| `assert_response_time` | `response`, `module_name` | `elapsed` ≤ module threshold in `SmokeTimeoutSeconds` | Module name, elapsed, threshold, URL | Performance smoke checks alongside `assert_response_status` |
| `assert_field` | `response`, `key`, `expected=None` | JSON has `key`; if `expected` set, value must match | Missing key / value mismatch / non-JSON | Single top-level JSON field presence or equality check |
| `assert_list_not_empty` | `response`, `key=None` | JSON (or `json[key]`) is a non-empty list | Not a list / empty / invalid JSON | List endpoints, search results, paginated first-page sanity |

> `module_name` is a `SmokeModule` constant — drives thresholds and expected statuses from `src/core/constants.py`.
> `assert_field` returns the field value so it can be chained into further checks.

```python
from core.constants import SmokeModule
from tests.commons.assertions import assert_status, assert_response_status, assert_response_time, assert_field, assert_list_not_empty

assert_status(response, 201)
assert_response_status(response, SmokeModule.HEALTH)
assert_response_time(response, SmokeModule.GENERIC_GET)

user_id = assert_field(response, "id")            # key must exist; returns value
assert_field(response, "status", "active")         # key must equal value

items    = assert_list_not_empty(response, "results")
all_rows = assert_list_not_empty(response)          # root is a JSON array
```

---

## Database assertions

Use these with rows/lists returned from `helpers.db_helper` (`fetch_row`, queries, etc.).

| Function | Parameters | Asserts | On Failure | When to Use |
|---|---|---|---|---|
| `assert_row_exists` | `row`, `label="DB row"` | `row is not None` | `"{label}: expected to find a row but got None"` | After `fetch_row` to confirm a record exists in DB |
| `assert_row_count` | `rows`, `expected`, `label="DB rows"` | `len(rows) == expected` | Expected vs actual count with label | Verifying an exact number of DB records |
| `assert_row_field` | `row`, `field`, `expected` | `row[field] == expected` (dict or object attribute) | Field name, expected vs actual value | Verifying a specific column value on a fetched row |

> `row` accepts a `dict` (uses `row.get(field)`), named tuple, or any object (uses `getattr`).
> `label` customises the failure message — use a meaningful name like `"user after signup"`.

```python
from tests.commons.assertions import assert_row_exists, assert_row_count, assert_row_field

row = fetch_row(db, "users", {"id": user_id})
assert_row_exists(row, label="user after signup")

rows = db.fetch_all("SELECT * FROM users WHERE user_id = %s", (user_id,))
assert_row_count(rows, 1, label="user logs")

assert_row_field(row, "email", "user@example.com")
assert_row_field(row, "active", True)
```

---

## Composed assertions (project-facing, `tests/commons/assertions.py` only)

| Function | Parameters | Asserts | When to Use |
|---|---|---|---|
| `assert_api_db_sync` | `api_record`, `db_record`, `field_mapping` | Each API field matches its mapped DB column, after normalising numeric strings / `"1"`/`"0"` booleans / whitespace | A write endpoint's response should match what actually landed in the DB |
| `assert_response_schema` | `record`, `schema`, `optional_fields=None` | Every schema field is present (unless in `optional_fields`) and `isinstance`-correct; collects all mismatches before failing | Locking down a response's shape once it's confirmed (see `tests/commons/api_schemas/`) |

```python
from tests.commons.assertions import assert_api_db_sync, assert_response_schema

assert_api_db_sync(
    api_record=response.json()["data"],
    db_record=user_row,
    field_mapping={"username": "username", "departmentId": "department_id"},
)

assert_response_schema(
    record=response.json(),
    schema={"id": int, "email": (str, type(None))},   # nullable
    optional_fields={"co_appraiser_id"},               # may be absent entirely
)
```

Do NOT wrap either side of an `assert_api_db_sync` comparison in `str()` — the normaliser handles
type differences; explicit casting defeats the purpose and can mask real type bugs.

---

## Module constants for smoke assertions

Pass these as `module_name` to `assert_response_status` / `assert_response_time`:

| Constant (`SmokeModule`) | Typical use |
|--------------------------|-------------|
| `HEALTH` | `/health`, `/status` |
| `DATABASE` | DB connectivity checks |
| `AUTH_SERVICE` | Auth health endpoints |
| `CONFIG` | Config/service metadata |
| `GENERIC_GET` | Other GET smoke paths |

Override thresholds and expected statuses in `src/core/constants.py` (`SmokeTimeoutSeconds`, `SmokeExpectedStatus`) for your project.

---

## Do not

- Reimplement status/body/row checks with bare `assert` when these helpers apply — you lose consistent failure messages.
- Import DB drivers into `helpers/assertions.py` or `tests/commons/assertions.py`; they only assert data you already fetched.
- Import from `helpers.assertions` directly in a test — always import from `tests.commons.assertions`, which re-exports every generic primitive plus the composed assertions above.

---

## Related helpers

| Module | Use for |
|--------|---------|
| `helpers.api_helper` | `authenticate_and_set_token`, `paginate_all` |
| `helpers.db_helper` | `fetch_row`, `insert_row`, `temp_row`, `compare_dicts` |

See `docs/TEST_PATTERNS.md` for stateful E2E and fixture patterns.
