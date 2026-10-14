# Project context

## Stack

- Python 3.12+, pytest, `requests`, Pydantic settings, Allure, pytest-xdist
- Example MySQL driver usage in `src/project/db/` only (not in core)

## Layout

| Path | Purpose |
|------|---------|
| `src/core/` | Config, API session, DB abstraction, state manager (driver-agnostic) |
| `src/fixtures/` | Reusable fixture factories |
| `src/helpers/` | Assertions, parsers, API/DB helpers, data builders (generic base classes) |
| `src/conftest.py` | Session-wide shared fixtures |
| `api/` | Typed API clients (`BaseAPIClient` subclasses), one per feature module |
| `tests/conftest.py` | **Project customization boundary** — override fixtures here |
| `tests/commons/` | Project-facing assertions, data builders, API schemas — shared across tiers |
| `tests/smoke/` | Health/connectivity (fast) |
| `tests/integration/` | GET + master tables: API count vs DB (read-only, no factories) |
| `tests/e2e/<feature>/` | Feature CRUD; factories from `tests/commons/data_builder/` only |
| `config/` | `.env.example` and `.env.*` (gitignored) |
| `docs/` | Human setup guides |

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env.dev   # then edit values
export ENV=dev

pytest tests/smoke -m smoke -ra
pytest tests/integration -m integration -ra
pytest tests/e2e -m e2e -ra
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

Prerequisites, access checklist, and the full "minimal changes to go live" list:
`docs/ONBOARDING.md`.
