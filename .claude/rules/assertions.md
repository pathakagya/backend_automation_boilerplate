# Assertion Standards

All assertion helpers live in `tests/commons/assertions.py`. Import only from there — never
write raw `assert` statements or inline validation loops in test files.

(Full parameter-by-parameter API reference: `.claude/context/assertions.md`. This file is the
Do/Don't rulebook; that one is the lookup table.)

## Dual validation — API + DB

Every test that modifies state MUST assert both:
1. The API response (status code, body)
2. The corresponding DB row after the write

Never assert only the HTTP response and skip the DB check.

```python
response = orders_api_client.create_order(payload)
assert_status(response, 201)

row = fetch_row(db_connection, "orders", {"id": response.json()["id"]})
assert_row_exists(row, label="order after creation")
assert_row_field(row, "status", "pending")
```

## API / DB sync

```python
assert_api_db_sync(api_record, db_record, field_mapping)
```

`field_mapping` is an explicit dict so the mapping stays readable, e.g.
`{"order_status": "STATUS", "total_amount": "TOTAL_AMT"}`. Values are normalised before
comparison (numeric strings, `"1"`/`"0"` booleans, whitespace) — do NOT wrap either side in
`str()` to force a match; that masks real type bugs.

## Response schema

```python
from tests.commons.assertions import assert_response_schema
from tests.commons.api_schemas.users_schemas import get_user_response_schema

assert_response_schema(
    record=response.json(),
    schema=get_user_response_schema(),
    optional_fields={"co_appraiser_id"},   # fields allowed to be entirely absent
)
```

- Always use `assert_response_schema` for field-presence/type checks — never write an inline
  `for field, expected_type in schema.items(): ...` loop in a test file.
- Schema dicts live in `tests/commons/api_schemas/{module}_schemas.py` (one file per module).
- A field typed `(SomeType, type(None))` is **nullable** (present, may be `None`). A field name
  passed in `optional_fields` may be **absent** from the payload entirely. These are different.

## Async DB writes — poll, don't sleep

If an endpoint triggers a background/async DB write, poll for the expected state before
asserting — never `time.sleep()`:

```python
from helpers.polling import wait_until

wait_until(
    lambda: fetch_row(db_connection, "orders", {"id": order_id}) is not None,
    timeout_seconds=15,
    description="order row visible in DB after async write",
)
row = fetch_row(db_connection, "orders", {"id": order_id})
assert_row_field(row, "status", "confirmed")
```

`wait_until` raises `PollingTimeoutError` on expiry — do not catch it in tests.

## What NOT to do

```python
# Bad — raw assert
assert response.status_code == 200

# Bad — str() cast masks real type bugs
if str(api_value) != str(db_value):
    ...

# Bad — inline schema loop
for field, expected_type in schema.items():
    assert field in record
    assert isinstance(record[field], expected_type)

# Bad — sleep instead of polling
time.sleep(3)
row = fetch_row(db_connection, "orders", {"id": order_id})
```

## Allure reporting

- Allure request/response attachment happens automatically at the `APISession` level (every HTTP
  call is attached). Assertion helpers do **not** auto-wrap in `allure.step` — wrap test steps
  yourself with `with allure.step("...")` for meaningful step names in the report.
- Use `@allure.feature` / `@allure.story` / `@allure.title` on test classes and methods.
