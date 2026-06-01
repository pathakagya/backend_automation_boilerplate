# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@.claude/context/agents.md
@.claude/context/project.md
@.claude/context/testing.md
@.claude/context/assertions.md
@.claude/context/gotchas.md

---

## Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env.dev   # fill in values
export ENV=dev

# Run tiers
make smoke          # pytest tests/smoke -m smoke
make integration    # pytest tests/integration -m integration
make e2e            # pytest tests/e2e -m e2e
make verify         # all three in order

# Single test
pytest tests/e2e/{feature}/test_{test_title}.py -ra -s
```

## Configuration

`ConfigManager` loads `config/.env.{ENV}` (e.g. `config/.env.dev`), falling back to `config/.env`. Env vars always override file values.

Key env vars:

| Variable | Purpose |
|----------|---------|
| `ENV` | Selects env file (`dev`, `staging`) |
| `API_BASE_URL` | Required — primary API base URL |
| `API_AUTH_TYPE` | `none` / `bearer` / `basic` |
| `API_TOKEN` | Bearer token (when `API_AUTH_TYPE=bearer`) |
| `API_USERNAME` / `API_PASSWORD` | Basic auth credentials |
| `DB_ENGINE` | `mysql` / `postgresql` / `oracle` |
| `DATABASE_HOST` / `PORT` / `NAME` / `USER` / `PASSWORD` | DB connection |
| `AUTH_SERVICE_BASE_URL` | Optional second service session |

## Architecture flow

Config (`ConfigManager`) → `APISession` / `DatabaseConnection` → `SharedTestResources` (wired in `tests/conftest.py`) → test fixtures → tests.

- `src/core/` is driver-agnostic; DB drivers live in `src/project/db/` only.
- `tests/conftest.py` dynamically imports the right DB class from `engine_map` based on `DB_ENGINE`.
- `src/conftest.py` owns session-wide boilerplate (`config`, `run_prefix`, `state`); never modify it for project-specific logic.
- `state` fixture (`StateManager`) is function-scoped; use it in e2e only to pass IDs between steps.
- `BaseFactory` produces plain dicts — no ORM, no DB writes — and belongs only in `tests/e2e/<feature>/factories.py`.

