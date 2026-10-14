# Generate API Client Skill

## 1. Name + Trigger

**Skill Name**: `generate-api-client`

**Trigger**: `/generate-api-client --module-name <name>`

**Description**: Scaffolds `api/<module_name>_client.py` — a class extending `BaseAPIClient`
with the inheritance/constructor boilerplate in place. No endpoint methods are pre-written; the
user adds them following the project's call patterns.

## 2. When to use

- Adding a new feature module that talks to the API (see `.claude/rules/new-module.md`).
- Migrating an existing raw `api_session.get/post(...)` call site to the typed-client pattern.

**Do not use** for a module that already has a client — add methods to the existing file instead.

## 3. Generated file

```python
"""Typed API client for the <Module Name> module."""
from __future__ import annotations

import requests

from api.base_client import BaseAPIClient


class <ModuleName>Client(BaseAPIClient):
    """Typed HTTP client for <module_name> endpoints.

    Add one method per endpoint below, named after the business action
    (e.g. `create_order`, not `post_order`). See .claude/rules/api-standards.md
    for the get/post/get_path/get_with_path/url_for patterns.
    """
```

No commented-out example methods, no placeholder endpoints — `BaseAPIClient` already documents
its own call patterns; duplicating them here just rots out of sync.

## 4. Naming derivation

- `module_name` → `snake_case` (e.g. `orders`, `payment_processing`)
- Class name → `PascalCase` + `Client` (e.g. `OrdersClient`, `PaymentProcessingClient`)
- Fixture name (added in the module's `conftest.py`, not by this skill) →
  `<module_name>_api_client`

## 5. After generation

1. Add one method per endpoint (see `.claude/rules/api-standards.md` for path-param /
   appended-segment / raw-URL patterns).
2. Add the corresponding path constant(s) to `src/core/constants.py::APIPath`.
3. Add a `<module_name>_api_client(api_session)` fixture in the module's `conftest.py`
   (`.claude/skills/generate-conftest/SKILL.md` can do this).
