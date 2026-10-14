# Integration tests

Integration tests independently compare API read results with project-owned
database queries. They are read-only by default and must not use factories.

Each project module should provide:

1. a typed API client method;
2. a verified schema/table/view registry;
3. a query helper using bound parameters;
4. a test marked `integration` and `db_required`;
5. a clear response-to-database mapping.

Example shape:

```python
import pytest
from helpers.integration import assert_api_db_count


@pytest.mark.integration
@pytest.mark.db_required
def test_orders_count(api_client, db_connection, order_registry):
    response = api_client.list_orders()
    assert response.status_code == 200
    db_count = order_registry.count_orders(db_connection)
    assert_api_db_count(response.json(), db_count, items_key="data", label="orders")
```

Do not put table names or guessed response keys in this generic directory.
Keep those facts in the consuming project's registry after verification.

