# Database Setup

> **Onboarding step 4 of 7** | Prev: [API_SETUP.md](API_SETUP.md) | Next: [TEST_PATTERNS.md](TEST_PATTERNS.md)

---

## Design principle

The core (`src/core/db_connection_manager.py`) defines an **abstract** `DatabaseConnection` class with no imports of any DB driver. This keeps the core driver-agnostic. Each supported engine lives in `src/project/db/`:

```
src/
├── core/
│   └── db_connection_manager.py   ← abstract base (no driver imports)
└── project/
    └── db/
        ├── mysql_connection.py      ← concrete MySQL implementation
        ├── postgresql_connection.py ← add your own if needed
        └── oracle_connection.py     ← add your own if needed
```

`tests/conftest.py` selects and loads the right class at runtime based on `DB_ENGINE`.

---

## Supported engines

| `DB_ENGINE` value | Module loaded | Class |
|-------------------|--------------|-------|
| `mysql` | `project.db.mysql_connection` | `MySQLConnection` |
| `postgresql` / `postgres` | `project.db.postgresql_connection` | `PostgreSQLConnection` |
| `oracle` | `project.db.oracle_connection` | `OracleConnection` |

If `DB_ENGINE` is not set or the required config vars are missing, all tests that use `db_connection` are **skipped** (not failed). This lets smoke tests run without any DB config.

---

## Step 1 — Set environment variables

Add to your `config/.env.dev`:

```ini
DB_ENGINE=mysql             # or postgresql / oracle

DATABASE_HOST=localhost
DATABASE_PORT=3306
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
1. Reads `DB_ENGINE` from config
2. Looks it up in `engine_map`
3. Validates all required keys (`host`, `port`, `name`, `user`, `password`)
4. Dynamically imports the connection class
5. Calls `.connect()` and returns the live connection
6. Skips the test (not fails) if any step cannot proceed

You do not need to change this code for MySQL — it works out of the box.

---

## Step 3 — Confirm DB access

Run the integration tier:

```bash
make integration
```

If DB config is correct, integration tests will run. If anything is missing, you'll see:

```
SKIPPED [1] tests/integration/...: Database config incomplete for mysql. Missing: host
```

---

## How to use `db_connection` in a test

```python
from helpers.db_helper import fetch_row, insert_row
from helpers.assertions import assert_row_exists, assert_row_field

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

## DB helper reference

| Helper | What it does |
|--------|-------------|
| `fetch_row(db, table, filters, schema)` | Returns first matching row as a dict, or `None` |
| `insert_row(db, table, data, schema)` | Inserts a row, returns inserted ID |
| `temp_row(db, table, data, schema)` | Context manager — inserts before, deletes after the test |
| `compare_dicts(actual, expected)` | Asserts all keys in `expected` exist and match in `actual` |


---

## Transaction isolation

Each test should leave the DB in the same state it found it. Rules:

- Use `temp_row` for rows you create in tests — it cleans up automatically.
- For manual inserts, use `yield` in fixtures to ensure rollback/cleanup.
- Never rely on test ordering; each test must be independently runnable.

---

## Adding a new database engine

1. Create `src/project/db/<engine>_connection.py` subclassing `DatabaseConnection`:

```python
# src/project/db/postgresql_connection.py
from core.db_connection_manager import DatabaseConnection

class PostgreSQLConnection(DatabaseConnection):
    def _create_connection(self):
        import psycopg2
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
        )

    def _create_cursor(self):
        return self._conn.cursor()    # or RealDictCursor for dict rows
```

2. Install the driver:

```bash
pip install psycopg2-binary
# add to requirements.txt
```

3. The `engine_map` in `tests/conftest.py` already has an entry for `postgresql`:

```python
engine_map = {
    "mysql":      ("project.db.mysql_connection",      "MySQLConnection"),
    "postgresql": ("project.db.postgresql_connection", "PostgreSQLConnection"),
    "oracle":     ("project.db.oracle_connection",     "OracleConnection"),
}
```

4. Set `DB_ENGINE=postgresql` in your `.env.dev` and run `make integration`.

---

## Common pitfalls

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Tests skipped with "Database config incomplete" | Missing one or more `DATABASE_*` vars | Add all required vars to `.env.dev` |
| `ImportError: No module named 'mysql.connector'` | Driver not installed | `pip install mysql-connector-python` |
| `Access denied for user` | Wrong user/password | Check `DATABASE_USER` and `DATABASE_PASSWORD` |
| `Can't connect to MySQL server` | Wrong host/port or DB not running | Verify `DATABASE_HOST:DATABASE_PORT` is reachable |
| Tests pass but data is left in DB | Missing cleanup | Wrap inserts in `temp_row` or use fixture teardown |

---

## Next step

→ [TEST_PATTERNS.md](TEST_PATTERNS.md) — learn the three test tier patterns (smoke, integration, e2e) with full code examples
