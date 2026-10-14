# Generate Test File Skill

## 1. Name + Trigger

**Skill Name**: `generate-test-file`

**Trigger**: `/generate-test-file --module-name <name> --tier <smoke|integration|e2e>`

**Description**: Scaffolds `tests/<tier>/<module_name>/test_<module_name>.py` with the
class/import/marker structure in place and Allure decorators wired — no template test methods.
The user writes the actual test cases.

## 2. When to use

- Right after `generate-conftest`, once the module's API client and fixtures exist.

**Do not use** to add one more test to an existing file — write it directly, matching the
existing style in that file.

## 3. Generated file shape (e2e example)

```python
"""Tests for the <Module Name> module."""
from __future__ import annotations

import allure
import pytest

from tests.commons.assertions import assert_status, assert_row_exists, assert_row_field
from tests.commons.data_builder import <ModuleName>Factory


@allure.feature("<Module Name>")
@pytest.mark.e2e
class Test<ModuleName>:
    """[Fill in scenarios: positive / negative / boundary — see .claude/rules/testing.md]"""
```

For `smoke`/`integration` tier, swap the marker and drop the factory import (per
`.claude/rules/testing.md`'s tier table — integration tests don't use `BaseFactory`).

## 4. Rules this must follow

- Class name `Test<ModuleName>` (`PascalCase`), one `@pytest.mark.<tier>` matching the folder.
- Import assertions from `tests.commons.assertions` — never a raw `assert`.
- No placeholder test methods — an empty class body with a `Fill in scenarios` docstring, not a
  fake `def test_example(): pass`.

## 5. After generation

1. Write test methods covering positive, negative, and boundary scenarios
   (`.claude/rules/testing.md` / `.claude/agents/quality-advocate.md` if present).
2. Each state-mutating test asserts both the API response and the DB row
   (`.claude/rules/assertions.md`'s dual-validation rule).
3. Run `pytest tests/<tier>/<module_name>/ -ra -s` before considering it done.
