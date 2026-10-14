# Setup Test Module Skill

## 1. Name + Trigger

**Skill Name**: `setup-test-module`

**Trigger**: `/setup-test-module --module-name <name> --tier <smoke|integration|e2e> [--description <desc>]`

**Aliases**: `/new-module`, `/create-test-module`

**Description**: Orchestrates the other four generation skills into one flow to scaffold a
complete new feature module: API client → conftest → data builder (e2e/integration-with-writes
only) → test file → constants/checklist. Generated files are immediately usable — the user adds
endpoint methods, factory field logic, and test cases after reviewing the structure.

## 2. When to use

- Adding a new feature module to the framework (orders, payments, a new dashboard, etc.).
- You want consistent boilerplate across client/conftest/data-builder/test-file without manual
  folder/naming errors.

**Do NOT use** when:
- Adding tests to an existing module — use its existing conftest/data builder.
- The module has no API client or DB access (a simpler ad-hoc test file may suffice).
- Refactoring/reorganizing an existing module — handle manually to avoid losing test data.

## 3. Step-by-step process

### Phase 1: Input & validation

- Gather: module name (snake_case), tier (`smoke`/`integration`/`e2e`), description (optional),
  known endpoints, known DB tables (optional).
- Validate: module doesn't already exist under `tests/<tier>/`; name is valid snake_case.

### Phase 2: Folder structure

```
tests/<tier>/<module_name>/
├── conftest.py
└── test_<module_name>.py
```
`api/` and `tests/commons/data_builder/` already exist — nothing to create there.

### Phase 3: Generate API client

Run `.claude/skills/generate-api-client/SKILL.md` → `api/<module_name>_client.py`.

### Phase 4: Generate conftest

Run `.claude/skills/generate-conftest/SKILL.md` → `tests/<tier>/<module_name>/conftest.py`.

### Phase 5: Generate data builder (e2e / write-heavy integration modules only)

Run `.claude/skills/generate-data-builder/SKILL.md` → `tests/commons/data_builder/<module_name>.py`.
Skip for read-only `integration` modules that only do count-parity checks.

### Phase 6: Generate test file

Run `.claude/skills/generate-test-file/SKILL.md` → `tests/<tier>/<module_name>/test_<module_name>.py`.

### Phase 7: Update project configuration

- Add any new table/column names and endpoint paths (`APIPath`) to `src/core/constants.py`.
- Add a schema file under `tests/commons/api_schemas/<module_name>_schemas.py` if the module's
  responses are worth structurally validating.

### Phase 8: Completion checklist

```
Completed:
  [x] Created tests/<tier>/<module_name>/ folder
  [x] Created api/<module_name>_client.py
  [x] Created tests/<tier>/<module_name>/conftest.py
  [x] Created tests/commons/data_builder/<module_name>.py (if applicable)
  [x] Created tests/<tier>/<module_name>/test_<module_name>.py

Next steps:
  [ ] Review generated files
  [ ] Implement API client methods
  [ ] Add endpoint paths to src/core/constants.py::APIPath
  [ ] Classify factory fields per CHECKLIST.md, implement factory methods
  [ ] Add module-specific fixtures (lookups, cleanup) to conftest.py
  [ ] Write test methods (positive / negative / boundary)
  [ ] Run: pytest tests/<tier>/<module_name>/ -ra -s
  [ ] Add new constants/schema to src/core/constants.py / tests/commons/api_schemas/
```

## 4. Key files referenced

| File | Purpose |
|------|---------|
| `api/base_client.py` | Base HTTP client class — parent for all typed clients |
| `tests/commons/data_builder/shared.py` | `BaseFactory` / `ProjectBaseFactory` — extend for module factories |
| `tests/commons/assertions.py` | Assertion helpers — use in tests |
| `src/core/constants.py` | Table/column/endpoint-path constants registry |
| `.claude/rules/new-module.md` | The manual checklist this skill automates |

## 5. Rules & standards

See `.claude/rules/testing.md`'s "Setup Test Module Skill Rules" section for the full Do/Don't
list this skill (and its constituent steps) must follow.
