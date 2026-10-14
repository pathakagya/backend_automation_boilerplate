# Database Standards (vendor-agnostic)

This boilerplate must work against **any** relational DB engine (MySQL, PostgreSQL, Oracle,
MSSQL, ...). The abstraction boundary already exists — don't reintroduce vendor-specific code
outside the one place it belongs.

## The abstraction boundary

- `src/core/db_connection_manager.py::DatabaseConnection` is the driver-agnostic abstract base
  — connect/disconnect lifecycle, `execute`/`fetch_one`/`fetch_all`, `transaction()` context
  manager, cleanup. It has **zero** driver imports.
- `src/project/db/<engine>_connection.py` is the **only** place a driver-specific import
  (`mysql.connector`, `psycopg2`, `cx_Oracle`/`oracledb`, `pyodbc`, ...) may appear. A new engine
  needs only `_create_connection()` and `_create_cursor()` implemented there.
- `tests/conftest.py`'s `TestResourcesManager.DB_ENGINE_MAP` dynamically imports the right class
  based on the `DB_ENGINE` env var. Test files never branch on engine.

**To add a new engine: create `src/project/db/<engine>_connection.py` and register it in
`DB_ENGINE_MAP` — test files and `helpers/db_helper.py` must not change.**

## Always go through `helpers/db_helper.py` / `helpers/db_operations.py`

Never write raw SQL placeholder strings (`%s`, `:1`, `?`, ...) directly in a test file — the
correct placeholder syntax depends on the configured engine's `paramstyle` and is handled
centrally:

```python
from helpers.db_helper import fetch_row, insert_row, temp_row

row = fetch_row(db_connection, "orders", {"customer_id": customer_id}, schema="app_schema")
with temp_row(db_connection, "orders", {"status": "pending"}) as row_data:
    ...  # test assertions
# row auto-deleted on exit
```

Every `DatabaseConnection` subclass declares a `paramstyle` class attribute (PEP 249 vocabulary:
`qmark` / `numeric` / `named` / `format` / `pyformat`). `helpers/db_helper.py` and
`helpers/db_operations.py` build placeholders from `conn.paramstyle` — never hardcode a
placeholder style in a helper or a test.

## Column/table name constants

- ALL table and column name references MUST use constants from `src/core/constants.py`
  (`DBTable`, etc.) — never hardcode a table/column string in a query or a factory.
- If a new column/table is needed, add its constant to `src/core/constants.py` first, then use
  it everywhere.

## Connection lifecycle

- `db_connection` (session-scoped, via `TestResourcesManager`) owns connect/cleanup — never
  open or close a connection manually inside a test.
- If a test suite holds a long-lived connection under a repeatable-read isolation level, reads
  may see a stale snapshot after another connection commits a write. Call `conn.commit()` (which
  ends the current transaction without changing data) immediately before a read that must see
  latest-committed state — see `tests/e2e/users/db_queries.py::_start_fresh_read` for the
  documented, confirmed-live example of this.

## Query organisation

- Reusable, cross-module queries belong in a shared module (see `tests/e2e/users/db_queries.py`
  for the pattern) — module-specific queries can live alongside the module's tests.
- Prefer `helpers/db_operations.py`'s higher-level helpers (`row_count`, `fetch_rows_by_field`,
  `bulk_insert`, `bulk_temp_rows`, `delete_where`, `update_row`) over hand-rolling a query when
  one already covers the case.
