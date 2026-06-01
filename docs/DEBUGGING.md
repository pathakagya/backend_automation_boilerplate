# Debugging

> **Onboarding step 7 of 7** | Prev: [EXTENDING.md](EXTENDING.md)

---

## First steps for any failure

Run the failing test in verbose mode with live stdout:

```bash
pytest tests/e2e/orders/test_order_crud.py::TestOrderCRUD::test_order_crud -vv -s
```

Check the Allure report for request/response details:

```bash
allure serve allure-results
```

Allure shows every API request, response body, and state snapshot attached by the helpers — this is usually the fastest path to the root cause.

---

## Common failures and fixes

### Smoke failures

#### `ConnectionError` or `requests.exceptions.ConnectionError`

```
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='api.example.com', port=443): Max retries exceeded
```

**Cause:** `API_BASE_URL` is wrong or the API is not reachable from your machine.

**Fix:**
1. Check the value: `echo $API_BASE_URL`
2. Confirm reachability: `curl -v $API_BASE_URL/health`
3. Check VPN / network access if the API is internal

---

#### `KeyError: 'base_url'` in fixture

```
KeyError: 'base_url'
```

**Cause:** `API_BASE_URL` is not set in the environment.

**Fix:**
```bash
export API_BASE_URL=https://api.example.com
# or add it to config/.env.dev
```

---

#### `AssertionError: health: expected status 200, got 503`

**Cause:** The API is up but the health endpoint is returning an error.

**Fix:** This is a real issue with the system under test, not a test framework problem. Notify the team.

---

### Config failures

#### `Required environment variable not set: ENV`

**Cause:** `ENV` is not exported in your shell.

**Fix:**
```bash
export ENV=dev
```

---

#### `config/.env.dev not found`

**Cause:** You haven't created the config file yet.

**Fix:**
```bash
cp config/.env.example config/.env.dev
# then fill in values
```

---

### Database failures

#### Tests skipped with "Database config incomplete"

```
SKIPPED [1] tests/integration/...: Database config incomplete for mysql. Missing: host
```

**Cause:** One or more `DATABASE_*` vars are missing.

**Fix:** Add all missing vars to `config/.env.dev` — see [ENV_CONFIG.md](ENV_CONFIG.md#database-connection).

---

#### `ImportError: No module named 'mysql.connector'`

**Cause:** DB driver not installed.

**Fix:**
```bash
pip install mysql-connector-python
```

---

#### `Access denied for user 'qa_user'@'localhost'`

**Cause:** Wrong `DATABASE_USER` or `DATABASE_PASSWORD`.

**Fix:** Check your DB credentials. Test the connection directly:
```bash
mysql -h $DATABASE_HOST -P $DATABASE_PORT -u $DATABASE_USER -p$DATABASE_PASSWORD $DATABASE_NAME
```

---

#### `Can't connect to MySQL server on 'localhost'`

**Cause:** Wrong `DATABASE_HOST` / `DATABASE_PORT`, or the DB server is not running.

**Fix:**
1. Check that the DB server is running
2. Confirm `DATABASE_HOST` and `DATABASE_PORT` in `.env.dev`
3. Check firewall rules / VPN

---

#### Test leaves data in the DB (dirty state)

**Cause:** Teardown is missing.

**Fix:** Wrap inserts in `temp_row` or add a `yield`-based fixture cleanup:

```python
# Option A: temp_row context manager
with temp_row(db, "users", payload, schema="app_schema") as user_id:
    # user is deleted after this block regardless of pass/fail

# Option B: fixture with yield teardown
@pytest.fixture
def created_user(api_session, db_connection):
    response = api_session.post("/users", json=UserFactory.build())
    user_id = response.json()["id"]
    yield user_id
    api_session.delete(f"/users/{user_id}")   # cleanup
```

---

### Auth failures

#### `401 Unauthorized` on every request

**Cause:** Wrong `API_AUTH_TYPE` or stale/expired token.

**Fix:**
1. Confirm `API_AUTH_TYPE` matches what the API expects
2. Refresh `API_TOKEN` in `.env.dev`
3. Check token expiry — if it's short-lived, use `authenticate_and_set_token` to refresh at runtime

---

#### `403 Forbidden`

**Cause:** The token is valid but the user doesn't have permission for that endpoint.

**Fix:** Use a user/token with the required role. Check with the API team what permissions are needed.

---

### Fixture failures

#### `fixture 'db_connection' not found`

**Cause:** You're trying to use `db_connection` in a smoke test, which doesn't have it in scope, or the fixture isn't imported.

**Fix:** Smoke tests don't get `db_connection`. If you need DB access, move the test to integration or e2e.

---

#### `NotImplementedError` in DB fixture

**Cause:** The abstract `DatabaseConnection` method was not implemented in your concrete subclass.

**Fix:** Open `src/project/db/<your>_connection.py` and implement the missing `_create_connection` or `_create_cursor` method.

---

### Test isolation failures

#### Test passes alone but fails in the full suite

**Cause:** The test depends on state left by a previous test (test ordering issue).

**Fix:**
1. Check that the test doesn't rely on data created by another test
2. Use `run_prefix` to namespace created data
3. Use `temp_row` or fixture teardown to clean up after each test

---

#### Parallel run (`-n auto`) causes data collisions

**Cause:** Multiple workers creating the same named entities.

**Fix:** Use `run_prefix` in factory-generated names so each worker's data is unique:
```python
payload = UserFactory.build(name=f"{run_prefix}_alice")
```

---

## Useful pytest flags

| Flag | What it does |
|------|-------------|
| `-vv` | Show full test names and assertion diffs |
| `-s` | Print stdout/print() to console (disables capture) |
| `-m smoke` | Run only smoke-marked tests |
| `-m "not e2e"` | Exclude e2e tests |
| `-k "test_user"` | Run only tests whose name contains "test_user" |
| `--tb=short` | Shorter traceback (less noise) |
| `--tb=long` | Full traceback (more context) |
| `--lf` | Re-run only the tests that failed last time |
| `-x` | Stop after the first failure |
| `--co` | Collect and list tests without running them |
| `-n auto` | Run in parallel with pytest-xdist (uses all CPU cores) |

**Examples:**

```bash
# Run a single test with full output
pytest tests/e2e/orders/test_order_crud.py::TestOrderCRUD::test_order_crud -vv -s

# Run all e2e tests for one feature
pytest tests/e2e/orders/ -m e2e -vv

# Run only failing tests from last run
pytest --lf -vv

# Collect tests without running
pytest tests/e2e/ --co -q
```

---

## Reading Allure reports

```bash
allure serve allure-results
```

In the Allure UI:
- **Suites** tab — test results grouped by file
- **Timeline** tab — which tests ran when (useful for parallel debugging)
- **Categories** tab — categorized failures (defined in `config/allure_categories.json`)
- Each test shows **steps** — every `with allure.step(...)` call appears here
- Each step shows the **request URL**, **response body**, and **status** attached by `APISession`

---

## Logs

| Log location | Content |
|-------------|---------|
| Terminal output | pytest progress + PASSED/FAILED per test |
| `allure-results/` | Allure JSON files for the HTML report |
| `testresult.log` | Raw pytest output from last run |

Enable verbose pytest log output by adding to your shell:
```bash
pytest tests/ -vv -s --log-cli-level=DEBUG
```

---

## Escalation checklist

If none of the above fixes the issue:

- [ ] Can you reproduce the failure with `-vv -s`?
- [ ] Does the failing assertion show the actual vs expected values?
- [ ] Does `allure serve allure-results` show the request/response that caused the failure?
- [ ] Is the same test passing on `main`? (`git stash && make smoke`)
- [ ] Is the API team aware of the issue?
- [ ] Is there a known deployment or schema change that could explain the diff?
