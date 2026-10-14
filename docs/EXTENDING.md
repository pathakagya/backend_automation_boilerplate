# Extending the Boilerplate

> **Onboarding step 6 of 7** | Prev: [TEST_PATTERNS.md](TEST_PATTERNS.md) | Next: [DEBUGGING.md](DEBUGGING.md)

---

## When to extend

You need to extend this boilerplate when:

- You're adding tests for a **new feature** in the product under test
- You're connecting to a **new API service** (a second microservice, a billing API, etc.)
- You're using a **different database engine** (PostgreSQL, Oracle)
- You need a **custom assertion helper** specific to your domain
- You need a **custom fixture** scoped to one feature area

---

## Checklist: adding a new feature test area

Here is the complete set of steps for adding tests for a new feature (e.g. `orders`):

```
tests/e2e/orders/
├── conftest.py               ← only if you need feature-scoped fixtures
└── test_order_crud.py        ← the actual test
tests/commons/data_builder/
└── orders.py                 ← OrderFactory extending ProjectBaseFactory, importable anywhere
tests/integration/
└── test_orders_count.py      ← API count vs DB count (read-only)
```

---

## Step-by-step: new feature (orders example)

### 1. Create the directory

```bash
mkdir -p tests/e2e/orders
touch tests/e2e/orders/__init__.py
```

### 2. Create the data factory

```python
# tests/commons/data_builder/orders.py
from helpers.common import random_string
from tests.commons.data_builder.shared import ProjectBaseFactory

class OrderFactory(ProjectBaseFactory):
    @classmethod
    def create_payload(cls, **overrides):
        payload = {
            "customer_name": f"customer_{random_string(6)}",
            "product_id": 1,
            "quantity": 1,
            "status": "pending",
        }
        payload.update(overrides)
        return payload

class BulkOrderFactory(OrderFactory):
    @classmethod
    def create_payload(cls, **overrides):
        return super().create_payload(quantity=100, **overrides)
```

Add `OrderFactory`/`BulkOrderFactory` to `tests/commons/data_builder/__init__.py`'s re-exports.

### 3. Create the integration count test

```python
# tests/integration/test_orders_count.py
import pytest
import allure
from helpers.api_helper import paginate_all

@pytest.mark.integration
class TestOrdersCount:

    @allure.title("API order count matches DB count")
    def test_order_count_parity(self, api_session, db_connection):
        api_orders = paginate_all(api_session, "/orders", items_key="data", next_key="next")
        row = db_connection.fetch_one("SELECT COUNT(*) AS total FROM orders")
        db_count = row["total"]
        assert len(api_orders) == db_count, f"API={len(api_orders)}, DB={db_count}"
```

### 4. Create the e2e CRUD test

```python
# tests/e2e/orders/test_order_crud.py
import pytest
import allure
from tests.commons.assertions import assert_status, assert_field, assert_row_exists, assert_row_field
from helpers.db_helper import fetch_row
from tests.commons.data_builder import OrderFactory

@pytest.mark.e2e
class TestOrderCRUD:

    @allure.title("Order lifecycle: create → read → update → delete")
    def test_order_crud(self, api_session, db_connection, state, run_prefix):
        payload = OrderFactory.create_payload(customer_name=f"{run_prefix}_order_test")

        with allure.step("POST /orders — create order"):
            response = api_session.post("/orders", json=payload)
            assert_status(response, 201)
            order_id = assert_field(response, "id")
            state.set("order_id", order_id)

        with allure.step("Assert order exists in DB"):
            row = fetch_row(db_connection, "orders", {"id": order_id}, schema="app_schema")
            assert_row_exists(row, label="order after create")
            assert_row_field(row, "status", "pending")

        with allure.step("PATCH /orders/{id} — update status"):
            response = api_session.patch(f"/orders/{order_id}", json={"status": "confirmed"})
            assert_status(response, 200)

        with allure.step("DELETE /orders/{id}"):
            response = api_session.delete(f"/orders/{order_id}")
            assert_status(response, 204)
```

### 5. (Optional) Add a feature conftest

Only create `tests/e2e/orders/conftest.py` if this feature needs dedicated fixtures (e.g. a pre-created product to attach orders to):

```python
# tests/e2e/orders/conftest.py
import pytest
from helpers.db_helper import temp_row

@pytest.fixture(scope="module")
def seeded_product(db_connection):
    """Ensures a product exists for order tests, cleaned up after the module."""
    with temp_row(db_connection, "products", {"name": "Test Product", "price": 9.99}, schema="app_schema") as product_id:
        yield product_id
```

### 6. Run the new tests

```bash
pytest tests/e2e/orders/ -m e2e -vv -s
pytest tests/integration/test_orders_count.py -m integration -vv -s
```

---

## Adding a new assertion helper

If an assertion appears more than once across your tests, extract it — into
**`tests/commons/assertions.py`** if it's specific to your product's domain (e.g. "order"
status), or into **`src/helpers/assertions.py`** only if it's genuinely generic and would be
useful in any fork of this boilerplate, independent of your business domain:

```python
# tests/commons/assertions.py  — add at the bottom of the file, and to __all__

def assert_order_status(order_response, expected_status: str) -> None:
    """Assert that an order response body contains the expected status."""
    actual = order_response.json().get("status")
    assert actual == expected_status, (
        f"Expected order status '{expected_status}', got '{actual}'. "
        f"URL: {order_response.url}"
    )
```

Then import it in your test:

```python
from tests.commons.assertions import assert_order_status

assert_order_status(response, "confirmed")
```

**Rules for assertion helpers:**
- Raise `AssertionError` with a message that includes expected, actual, and context (URL, label)
- Never do HTTP calls or DB queries inside an assertion helper
- Do not import DB drivers into `helpers/assertions.py` or `tests/commons/assertions.py`
- Tests import assertions from `tests.commons.assertions` only — see `.claude/rules/assertions.md`

---

## Adding a second API service

Set up with `make_api_fixture` — full steps (env vars, config resolution) in
[API_SETUP.md § "Second services / multi-API setup"](API_SETUP.md#second-services--multi-api-setup).
Once `billing_session = make_api_fixture("billing_api")` is added to `tests/conftest.py`, use it
alongside your feature's typed client:

```python
def test_invoice_created(orders_api_client, billing_session):
    response = orders_api_client.create_order({...})
    order_id = response.json()["id"]

    invoice = billing_session.get(f"/invoices?order_id={order_id}")
    assert invoice.status_code == 200
```

---

## Adding a new database engine

See the dedicated section in [DATABASE_SETUP.md](DATABASE_SETUP.md#adding-a-new-database-engine).

Summary:
1. Create `src/project/db/<engine>_connection.py` subclassing `DatabaseConnection`
2. Add the driver to `requirements.txt`
3. Set `DB_ENGINE=<engine>` in `.env.dev`

The `DB_ENGINE_MAP` in `src/core/test_resources.py` already has entries for `mysql`, `postgresql`, and `oracle`.

---

## What NOT to do

| Don't | Why |
|-------|-----|
| Put factories in `tests/integration/` | Integration tests are read-only; factories imply data creation |
| Import DB drivers in `src/core/` | Core must remain driver-agnostic |
| Modify `src/conftest.py` for project logic | That file is boilerplate-wide; use `tests/conftest.py` |
| Add `tests/unit/` | Unit tests belong in the backend app repo, not here |
| Hard-code base URLs in tests | Use `api_session` which reads from config |
| Share state between tests via module-level variables | Use the `state` fixture scoped to the function |

---

## Next step

→ [DEBUGGING.md](DEBUGGING.md) — diagnose failures, read logs, and common fixes
