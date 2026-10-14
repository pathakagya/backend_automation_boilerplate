# Database Setup

> **Onboarding step 4 of 7** | Prev: [API_SETUP.md](API_SETUP.md) | Next: [TEST_PATTERNS.md](TEST_PATTERNS.md)

---

## The DB layer at a glance

Five files own the database stack, mirroring the API layer's shape
([API_SETUP.md](API_SETUP.md)): one abstract transport, one concrete per-engine implementation,
one dynamic loader, one DAO helper layer, and one opt-in fixture factory for extra connections.

```
config/.env.dev  (DB_ENGINE, DATABASE_HOST, ...)
        │
        ▼
ConfigManager.get_database_config()                  ← src/core/config_manager.py
        │
        ▼
TestResourcesManager.get_db_connection()              ← src/core/test_resources.py
        │   reads DB_ENGINE, looks it up in DB_ENGINE_MAP, imports the matching class
        ▼
DatabaseConnection (abstract)                         ← src/core/db_connection_manager.py
        │   connect/disconnect lifecycle, execute/fetch_one/fetch_all, transaction(), paramstyle
        ▼
MySQLConnection / PostgreSQLConnection / OracleConnection  ← src/project/db/
        │   one file per engine; the ONLY place driver imports appear — built ONCE per
        │   session by tests/conftest.py's `db_connection` fixture
        ▼
db_helper.py / db_operations.py (DAO layer)            ← src/helpers/
        │   fetch_row, insert_row, temp_row, row_count, bulk_insert, ... — paramstyle-agnostic
        ▼
Tests                                                  ← tests/integration|e2e/
```

`src/fixtures/database_fixtures.py` sits alongside this chain rather than in it — it's an
opt-in factory for a **second** database connection, not where your default `db_connection`
comes from (same relationship `api_fixtures.py` has to the API chain).

---

## File-by-file reference

| File | What it is | Owns |
|------|-----------|------|
| `src/core/db_connection_manager.py` | `DatabaseConnection` abstract base | connect/disconnect lifecycle, `execute`/`fetch_one`/`fetch_all`, `transaction()` context manager, the `paramstyle` contract. **Zero driver imports** — the abstraction boundary. |
| `src/project/db/mysql_connection.py` | `MySQLConnection(DatabaseConnection)` | Imports `mysql.connector`. |
| `src/project/db/postgresql_connection.py` | `PostgreSQLConnection(DatabaseConnection)` | Imports `psycopg2`; uses `RealDictCursor` for dict rows. |
| `src/project/db/oracle_connection.py` | `OracleConnection(DatabaseConnection)` | Imports `oracledb` (thin mode); overrides `execute()` to set `rowfactory` for dict rows after each query. |
| `src/core/test_resources.py` | `TestResourcesManager.get_db_connection` | Dynamically imports the project-owned adapter from `DB_ADAPTER_CLASS`; `DB_ENGINE=mysql` remains a compatibility shortcut for the Vyaguta/reference adapter. Missing DB capability is an actionable error, not a silent skip. |
| `src/core/db_adapter.py` | `DatabaseAdapter` protocol | Documents the project-owned adapter contract: lifecycle, parameterized queries, transactions, seed/cleanup, and safe diagnostics. |
| `src/helpers/db_helper.py` | `fetch_row`, `insert_row`, `temp_row`, `compare_dicts` | The core DAO helpers — paramstyle-agnostic single-table reads/writes and DB↔dict comparison. |
| `src/helpers/db_operations.py` | `bulk_insert`, `bulk_temp_rows`, `fetch_rows_by_field`, `fetch_by_multiple_fields`, `row_count`, `table_exists`, `delete_where`, `update_row` | Higher-level operations built on `db_helper.py` — prefer these over hand-rolling a query when one already covers the case. |
| `src/fixtures/database_fixtures.py` | `make_db_fixture` | Opt-in pytest fixture factory for an **additional**, differently-configured connection (a second DB, or an engine other than your primary one). |

---

## Design principle

The core (`src/core/db_connection_manager.py`) defines an abstract `DatabaseConnection` class
with no imports of any DB driver — this keeps the core driver-agnostic. Each supported engine
lives in `src/project/db/`:

```
src/
├── core/
│   └── db_connection_manager.py   ← abstract base (no driver imports)
└── project/
    └── db/
        ├── mysql_connection.py      ← MySQL implementation (Vyaguta reference)
        ├── postgresql_connection.py ← PostgreSQL implementation
        └── oracle_connection.py     ← Oracle implementation
```

`tests/conftest.py`'s `db_connection` fixture (via `TestResourcesManager`) selects and loads the
project-owned adapter at runtime. Set `DB_ADAPTER_CLASS=package.module:Class` for a consuming
project. `DB_ENGINE=mysql` is retained only for the working Vyaguta/reference setup.

---

## Supported engines

All three adapters ship with the boilerplate. Install only the driver package for your engine —
nothing else needs to change.

| `DB_ENGINE` value | Adapter class | Driver package | `paramstyle` |
|---|---|---|---|
| `mysql` | `MySQLConnection` | `mysql-connector-python` | `format` (`%s`) |
| `postgresql` / `postgres` | `PostgreSQLConnection` | `psycopg2-binary` | `format` (`%s`) |
| `oracle` | `OracleConnection` | `oracledb` (thin mode, no Instant Client) | `numeric` (`:1`) |

**No driver is installed by default.** See [Step 1a](#step-1a--install-your-db-driver) below.

If a DB-backed test requests `db_connection` without a usable adapter or complete configuration,
it fails with an actionable setup error. API-only smoke tests do not request that fixture and
remain runnable without DB configuration:

```bash
pytest -m "smoke and not db_required" -ra
```

---

## Step 1a — Install your DB driver

No driver is installed by default. Install the one for your engine (pick one):

```bash
# MySQL
pip install mysql-connector-python>=9.0.0

# PostgreSQL
pip install psycopg2-binary>=2.9.9

# Oracle (thin mode — no Oracle Instant Client needed)
pip install oracledb>=2.0.0
```

See `requirements-db.txt` at the repo root for the full list with pinned versions. Add your
chosen line to that file (uncommented) so teammates and CI use the same pin.

**CI:** Set the `DB_DRIVER` repo variable (Settings → Variables → Actions) to the package spec
(e.g. `psycopg2-binary>=2.9.9`). The `db-tests` job installs it automatically.

---

## Step 1b — Set environment variables

Add to your `config/.env.dev`:

```ini
DB_ENGINE=postgresql          # or mysql / oracle

DATABASE_HOST=localhost
DATABASE_PORT=5432            # 3306 for MySQL, 1521 for Oracle
DATABASE_NAME=app_db
DATABASE_USER=qa_user
DATABASE_PASSWORD=qa_password
```

---

## Step 2 — Verify the fixture is wired

Open `tests/conftest.py`. The `db_connection` fixture is already wired via `SharedTestResources`:

```python
@pytest.fixture(scope="session")
def db_connection(config, shared_test_resources):
    return shared_test_resources.get_db_connection(config)
```

`get_db_connection()` does the following automatically:
1. Reads `DB_ADAPTER_CLASS` (or the reference `DB_ENGINE` alias) from config.
2. Validates all required keys (`host`, `port`, `name`, `user`, `password`).
3. Dynamically imports the project-owned adapter class.
4. Calls `.from_config()`, `.connect()`, and returns the live adapter.
5. Raises a clear `DatabaseAdapterUnavailable` error if setup cannot proceed.

You do not need to change this code for MySQL — it works out of the box.

---

## Step 3 — Confirm DB access

Run the integration tier:

```bash
pytest tests/integration -m integration -ra
```

If DB config is correct, integration tests will run. If anything is missing, you'll see:

```
SKIPPED [1] tests/integration/...: Database config incomplete for mysql. Missing: host
```

---

## How to use `db_connection` in a test

```python
from helpers.db_helper import fetch_row, insert_row
from tests.commons.assertions import assert_row_exists, assert_row_field

def test_user_in_db(api_session, db_connection):
    # Create via API
    response = api_session.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    user_id = response.json()["id"]

    # Assert it landed in the DB
    row = fetch_row(db_connection, "users", {"id": user_id}, schema="app_schema")
    assert_row_exists(row, label="user after create")
    assert_row_field(row, "email", "alice@example.com")
```

---

## The DAO layer: `db_helper.py` and `db_operations.py`

Every function below takes an already-connected `DatabaseConnection` as its first argument and
builds placeholders from `conn.paramstyle` — never hardcode `%s`/`?`/`:1` in a test; these
helpers are what stay portable across engines. See `.claude/rules/db-standards.md`.

### `src/helpers/db_helper.py` — core helpers

| Helper | What it does |
|--------|-------------|
| `fetch_row(db, table, where, schema)` | Returns the first row matching an equality `WHERE`, as a dict, or `None` |
| `insert_row(db, table, data, schema)` | Inserts a row, commits, and returns the auto-generated primary key (`cursor.lastrowid`) — or `None` if the table/driver doesn't expose one |
| `temp_row(db, table, data, schema, pk_column="id")` | Context manager — inserts before, deletes after, by `pk_column` using the id `insert_row` returned (falls back to matching the original values only if no id is available) |
| `compare_dicts(expected, actual, fields=None)` | Asserts every key in `expected` matches `actual` (dict or object) |

### `src/helpers/db_operations.py` — higher-level operations

| Helper | What it does |
|--------|-------------|
| `bulk_insert(db, table, rows, schema)` | Inserts multiple rows, returns the count inserted |
| `bulk_temp_rows(db, table, rows, schema, pk_column="id")` | Context manager — inserts multiple rows, deletes each by `pk_column` afterward (same by-id cleanup as `temp_row`) |
| `fetch_rows_by_field(db, table, field, value, schema)` | All rows matching a single field |
| `fetch_by_multiple_fields(db, table, where, schema)` | All rows matching several field conditions |
| `row_count(db, table, schema, where=None)` | `COUNT(*)`, optionally filtered |
| `table_exists(db, table, schema)` | Best-effort existence check (`SELECT 1 ... LIMIT 1`) |
| `delete_where(db, table, where, schema)` | Deletes matching rows, returns rows deleted |
| `update_row(db, table, set_values, where, schema)` | Updates matching rows, returns rows updated |

> **Why delete-by-id matters:** `temp_row`/`bulk_temp_rows` clean up by the row's actual primary
> key, not by matching the column values you inserted with — matching on values would also
> delete any other row in the table that happens to share them (e.g. another row with the same
> `status`). If you need a table without an auto-increment PK, pass the real key explicitly in
> `data`/`rows` (e.g. include `"id": known_id`) — an explicit id you provide always wins over
> the driver's `lastrowid`.

### When the generic helpers aren't enough

For multi-table joins, `ORDER BY`, or a schema-specific cascading delete, write dedicated query
functions instead of forcing them through the single-table generic helpers — see
`tests/e2e/users/db_queries.py` for the real, worked pattern (and its `_start_fresh_read()`
helper, described in "Transaction isolation" below).

---

## A second / named database connection

Use `make_db_fixture` from `src/fixtures/database_fixtures.py` for an additional connection —
a second database, or an engine different from your primary one:

```python
# tests/conftest.py
from fixtures.database_fixtures import make_db_fixture
from project.db.oracle_connection import OracleConnection   # your subclass

analytics_db = make_db_fixture(OracleConnection, config_section="oracle", scope="session")
```

```ini
ORACLE_ENGINE=oracle
ORACLE_HOST=oracle.example.com
ORACLE_PORT=1521
ORACLE_NAME=orcl
ORACLE_USER=qa_user
ORACLE_PASSWORD=qa_password
```

`make_db_fixture(connection_class, config_section)` calls
`config.get_database_config(config_section)`, which reads `{SECTION}_HOST`, `{SECTION}_PORT`,
etc. for any section name other than the default `"database"` — same env-var-visibility rule as
[API_SETUP.md's second-services note](API_SETUP.md#second-services--multi-api-setup) (values in
`config/.env.{ENV}` are loaded automatically; in CI, set them as real secrets/env vars).

Unlike the primary `db_connection` fixture, `make_db_fixture` does **not** gracefully skip on
incomplete config — a missing `{SECTION}_PORT` etc. raises a normal error at connection time
rather than a `pytest.skip`.

---

## Transaction isolation

Each test should leave the DB in the same state it found it. Rules:

- Use `temp_row`/`bulk_temp_rows` for rows you create in tests — they clean up automatically, by
  primary key (see the DAO layer section above).
- For manual inserts, use `yield` in fixtures to ensure rollback/cleanup.
- Never rely on test ordering; each test must be independently runnable.
- If a test suite holds a long-lived connection under a repeatable-read isolation level (MySQL's
  default), reads on that connection can see a stale snapshot after another connection (e.g. the
  API under test) commits a write — even moments earlier. Call `conn.commit()` immediately before
  a read that must see latest-committed state; it ends the current transaction without changing
  data, so the next statement opens a fresh snapshot. See `tests/e2e/users/db_queries.py`'s
  `_start_fresh_read()` for the documented, confirmed-live example.

---

## Adding a custom database engine

MySQL, PostgreSQL, and Oracle adapters are included. For any other engine (MSSQL, SQLite,
Snowflake, etc.):

1. Create `src/project/db/<engine>_connection.py` subclassing `DatabaseConnection`. Implement
   `_create_connection()` and `_create_cursor()`. Set `paramstyle` to match the driver:

   | Driver | `paramstyle` | Placeholder |
   |---|---|---|
   | psycopg2, mysql-connector | `"format"` | `%s` |
   | oracledb, cx_Oracle | `"numeric"` | `:1` |
   | pyodbc, sqlite3 | `"qmark"` | `?` |

   Leaving `paramstyle` unset inherits `"format"` — correct for MySQL/PostgreSQL, wrong for
   Oracle or pyodbc engines.

2. Register the engine in `DB_ENGINE_MAP` in `src/core/test_resources.py`:

   ```python
   "snowflake": ("project.db.snowflake_connection", "SnowflakeConnection"),
   ```

   Or skip registration and use `DB_ADAPTER_CLASS=project.db.snowflake_connection:SnowflakeConnection`.

3. Install the driver (`pip install <driver>`) and add it to `requirements-db.txt`.

4. Set `DB_ENGINE=<engine>` in `.env.dev` and run `pytest tests/integration -m integration -ra`.

---

## Common pitfalls

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Tests skipped with "Database config incomplete" | Missing one or more `DATABASE_*` vars | Add all required vars to `.env.dev` |
| `ImportError: No module named 'mysql.connector'` | MySQL driver not installed | `pip install mysql-connector-python>=9.0.0` |
| `ImportError: No module named 'psycopg2'` | PostgreSQL driver not installed | `pip install psycopg2-binary>=2.9.9` |
| `ImportError: No module named 'oracledb'` | Oracle driver not installed | `pip install oracledb>=2.0.0` |
| `Access denied for user` | Wrong user/password | Check `DATABASE_USER` and `DATABASE_PASSWORD` |
| `Can't connect to MySQL server` / `connection refused` | Wrong host/port or DB not running | Verify `DATABASE_HOST:DATABASE_PORT` is reachable |
| A read intermittently returns `None`/stale data right after a write | Long-lived connection under repeatable-read isolation | Call `conn.commit()` before the read — see "Transaction isolation" above |
| `make_db_fixture(section=...)` connects to the wrong host | `{SECTION}_*` vars not actually visible in the process env | Confirm they're in `config/.env.{ENV}` (loaded automatically) or exported in the shell/CI |
| Query raises a syntax error on a new engine (`:1` not valid MySQL`, etc.) | Hardcoded placeholder style instead of `helpers.common.placeholder(conn.paramstyle, ...)` | Never hardcode `%s`/`?`/`:1` — always build placeholders from `conn.paramstyle`, and set that class attribute correctly on your new engine's subclass |
| `temp_row`/`bulk_temp_rows` seems to delete more than the test created | You're on an older version without by-id cleanup, or the table has no auto-increment PK | Update, or pass the real key explicitly via `pk_column`/an explicit id in `data` |

---

## Next step

→ [TEST_PATTERNS.md](TEST_PATTERNS.md) — learn the three test tier patterns (smoke, integration, e2e) with full code examples
