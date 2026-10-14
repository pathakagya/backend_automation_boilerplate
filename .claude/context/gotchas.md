# Gotchas

Add entries here only after an agent repeats the same mistake. Prune stale items regularly.

## Fixture overrides

- Override `db_connection` and project-specific API fixtures in **`tests/conftest.py`**, not `src/conftest.py`.
- `src/conftest.py` is for boilerplate-wide defaults shared across forks of this template.

## Imports

- Tests and `src/` code import as `from core.xyz import ...` because `pythonpath = src` is set in `pytest.ini`.
- Do not add `src/` to individual import paths in new modules.

## Secrets

- Never commit `config/.env`, `config/.env.dev`, or `config/.env.staging`.
- Use `config/.env.example` as the template only.

## Core purity

- Database drivers belong in `src/project/db/` (or your project package), never in `src/core/`.

## Test folder boundaries

- **`tests/integration/`** — count parity on GET/list endpoints and master tables only. No CRUD, no factory `.create_payload()` calls for payloads.
- **`tests/e2e/`** — feature CRUD and multi-step flows. `state` belongs here only; data factories live in `tests/commons/data_builder/` but are likewise only *used* in e2e tests.
- Do not add count-parity tests under `tests/e2e/` or CRUD/factory tests under `tests/integration/`.

## Assertions and data builders

- Tests import assertions from **`tests.commons.assertions`**, not `helpers.assertions` directly
  — the former re-exports the generic primitives and adds the project-facing composed ones
  (`assert_api_db_sync`, `assert_response_schema`). See `.claude/rules/assertions.md`.
- Feature factories extend `ProjectBaseFactory` (`tests/commons/data_builder/shared.py`), not
  `BaseFactory` (`src/helpers/data_builders.py`) directly.
