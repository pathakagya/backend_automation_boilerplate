# Generate Conftest Skill

## 1. Name + Trigger

**Skill Name**: `generate-conftest`

**Trigger**: `/generate-conftest --module-name <name> --tier <smoke|integration|e2e>`

**Description**: Scaffolds a module-level `tests/<tier>/<module_name>/conftest.py` with the
fixtures every module needs, wired to the already-existing global fixtures
(`api_session`, `db_connection`, `state`) rather than redefining them.

## 2. When to use

- Right after `generate-api-client`, when setting up a brand-new feature module.
- **Do not use** to add one-off fixtures to an existing module's conftest — edit it directly.

## 3. Generated file

```python
"""Module fixtures for <module_name>."""
from __future__ import annotations

import pytest

from api.<module_name>_client import <ModuleName>Client


@pytest.fixture(scope="module")
def <module_name>_api_client(api_session) -> <ModuleName>Client:
    return <ModuleName>Client(api_session)
```

For `e2e` tier modules, also include:

```python
@pytest.fixture
def <module_name>_cleanup(db_connection):
    """Tracks created <module_name> IDs and deletes them after each test."""
    created_ids: list = []
    yield created_ids
    for item_id in created_ids:
        # delete via helpers.db_operations.delete_where or a DELETE endpoint
        pass
```

No template fixtures beyond these — the user adds module-specific lookup/precondition fixtures
as the tests reveal a need for them (don't guess at fixtures the module doesn't need yet).

## 4. Rules this must follow

- `<module_name>_api_client` is always module-scoped and named `<module_name>_api_client` — see
  `.claude/rules/testing.md`'s naming convention.
- Never redefine `api_session`, `db_connection`, or `state` here — those live in
  `tests/conftest.py` / `src/conftest.py`.
- Absolute imports only (`pythonpath = src`).

## 5. After generation

1. Fill in the cleanup fixture's deletion logic if the module is `e2e` tier.
2. Add any module-specific DB lookup fixtures as tests need them.
3. Run `pytest tests/<tier>/<module_name>/ --collect-only` to confirm the conftest loads.
