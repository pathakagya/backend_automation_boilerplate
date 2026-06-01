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

- **`tests/integration/`** — count parity on GET/list endpoints and master tables only. No CRUD, no `BaseFactory.build()` for payloads.
- **`tests/e2e/`** — feature CRUD and multi-step flows. Data factories and `state` belong here only.
- Do not add count-parity tests under `tests/e2e/` or CRUD/factory tests under `tests/integration/`.
