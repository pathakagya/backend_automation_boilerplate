# Generate Data Builder Skill

## 1. Name + Trigger

**Skill Name**: `generate-data-builder`

**Trigger**: `/generate-data-builder --module-name <name> --sample-payload <json or description>`

**Description**: Scaffolds `tests/commons/data_builder/<module_name>.py` — a factory class
extending `ProjectBaseFactory`, with fields classified per `CHECKLIST.md` and a
`create_payload(**overrides)` method that returns a plain dict.

## 2. When to use

- Adding a new feature module that needs to POST/PUT payloads.
- A payload shape has grown enough ad-hoc dict-literal duplication across tests that it needs a
  factory.

**Do not use** to add one field to an existing factory — edit it directly and keep the
`**overrides` merge as the extension point.

## 3. Before generating — classify every field

Read `CHECKLIST.md` and classify each field in the sample payload into one of six buckets before
writing any code. This is the step that prevents flaky/incorrect test data — do not skip it.

## 4. Generated file shape

```python
"""Data factory for the <Module Name> module."""
from __future__ import annotations

import random
from typing import Any

from tests.commons.data_builder.shared import ProjectBaseFactory


class <ModuleName>Factory(ProjectBaseFactory):
    _VALID_STATUSES = ("pending", "active", "closed")   # enum bucket — explicit, not Faker

    @classmethod
    def create_payload(cls, *, customer_id: int, **overrides: Any) -> dict[str, Any]:
        payload = {
            "customer_id": customer_id,                          # ID bucket — required kwarg
            "created_by": "AUTOMATION",                           # audit bucket — hardcoded
            "status": random.choice(cls._VALID_STATUSES),         # enum bucket
            "notes": cls._faker.sentence(),                       # text bucket — Faker
            "amount": cls._faker.pyfloat(min_value=1, max_value=1000, right_digits=2),  # number
            "due_date": cls._faker.future_date().isoformat(),     # date bucket — Faker
        }
        payload.update(overrides)
        return payload
```

No template/placeholder methods beyond what the sample payload's fields require — this file
should be immediately usable, not a stub the user has to gut.

## 5. After generation

1. Add the new factory class to `tests/commons/data_builder/__init__.py`'s re-exports.
2. If the module needs multiple related payload shapes (create vs. update vs. status-change),
   add one method per shape, each delegating to `create_payload` where possible (see
   `tests/commons/data_builder/shared.py` for the base-class-plus-subclass-adds-variants
   pattern already used by `UserFactory`).
