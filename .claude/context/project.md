# Project context

## Stack

- Python 3.12+, pytest, `requests`, Pydantic settings, Allure, pytest-xdist
- Example MySQL driver usage in `src/project/db/` only (not in core)

## Layout

| Path | Purpose |
|------|---------|
| `src/core/` | Config, API session, DB abstraction, state manager (driver-agnostic) |
| `src/fixtures/` | Reusable fixture factories |
| `src/helpers/` | Assertions, parsers, API/DB helpers, data builders |
| `src/conftest.py` | Session-wide shared fixtures |
| `tests/conftest.py` | **Project customization boundary** — override fixtures here |
| `tests/smoke/` | Health/connectivity (fast) |
| `tests/integration/` | GET + master tables: API count vs DB (read-only, no factories) |
| `tests/e2e/<feature>/` | Feature CRUD; `BaseFactory` only here |
| `config/` | `.env.example` and `.env.*` (gitignored) |
| `docs/` | Human setup guides |

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env.dev   # then edit values
export ENV=dev

make smoke | make integration | make e2e | make verify
```

## Configuration

- `ENV=dev` or `ENV=staging` before running tests
- `ConfigManager`: INI, YAML, env; env vars override files
- `pytest.ini`: `pythonpath = src` → `from core.xyz import ...`

## Design constraints

- No DB driver imports in `src/core/`
- Config helpers return plain dicts
- Fixture teardown uses explicit `yield`
- `state` fixture is function-scoped (`StateManager`) — e2e only

## First-time fork checklist

1. `config/.env.dev` from `.env.example`
2. `tests/conftest.py` — API + DB sessions
3. `src/core/constants.py` — endpoints, smoke defaults, master tables
4. `src/project/db/` — DB driver implementation
5. `make smoke`
