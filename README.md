# Pytest Automation Boilerplate

Scalable, AI-first test automation framework for backend API and database validation.

---

## What this gives you

- Reusable core for config, API sessions, DB abstraction, and state management
- Three-tier test structure: smoke → integration → e2e
- Hierarchical fixtures with clean teardown patterns
- Allure reporting with request/response attachments
- Support for MySQL, PostgreSQL, Oracle
- Parallel test execution via pytest-xdist

---

## New QA engineer? Start here.

Follow the docs below **in order**. Each doc ends with a link to the next one.

| Step | Doc | What you'll do |
|------|-----|----------------|
| 1 | [QUICK_START.md](docs/QUICK_START.md) | Set up the local environment and run your first smoke test |
| 2 | [ENV_CONFIG.md](docs/ENV_CONFIG.md) | Understand every config variable and how the loader resolves them |
| 3 | [API_SETUP.md](docs/API_SETUP.md) | Configure authentication and multi-service API sessions |
| 4 | [DATABASE_SETUP.md](docs/DATABASE_SETUP.md) | Wire the database connection |
| 5 | [TEST_PATTERNS.md](docs/TEST_PATTERNS.md) | Learn the smoke / integration / e2e test patterns with full examples |
| 6 | [EXTENDING.md](docs/EXTENDING.md) | Add tests for a new feature area from scratch |
| 7 | [DEBUGGING.md](docs/DEBUGGING.md) | Diagnose failures, read logs, common fixes |

---

## Setup and Execution

### macOS / Linux

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp config/.env.example config/.env.dev
# Edit config/.env.dev with your API_BASE_URL and DB credentials

# 4. Set environment variable
export ENV=dev

# 5. Run tests
make smoke              # fast health/connectivity checks
make integration        # API count vs DB (requires DB config)
make e2e                # CRUD flows (requires DB config)
make verify             # all three in order
```

### Windows

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy config\.env.example config\.env.dev
# Edit config\.env.dev with your API_BASE_URL and DB credentials (use Notepad or your IDE)

# 4. Set environment variable
set ENV=dev

# 5. Run tests (use pytest directly — Make is not available on Windows)
pytest tests/smoke -m smoke -ra                    # fast health/connectivity checks
pytest tests/integration -m integration -ra        # API count vs DB (requires DB config)
pytest tests/e2e -m e2e -ra                        # CRUD flows (requires DB config)

# All tests in order (smoke → integration → e2e)
pytest tests/smoke -m smoke -ra && pytest tests/integration -m integration -ra && pytest tests/e2e -m e2e -ra
```

> **⚠️ Note:** The `Makefile` uses Unix-style commands and does not work on Windows. Windows users must use `pytest` commands directly.

---

## Test tiers

| Tier | Folder | Marker | Purpose |
|------|--------|--------|---------|
| Smoke | `tests/smoke/` | `@pytest.mark.smoke` | Health & connectivity — no DB required |
| Integration | `tests/integration/` | `@pytest.mark.integration` | API list count vs DB count (read-only, no factories) |
| E2E | `tests/e2e/<feature>/` | `@pytest.mark.e2e` | Feature CRUD; `BaseFactory` payloads; `state` fixture |

---

## Project layout

```
pytest-automation-boilerplate/
├── config/
│   └── .env.example          ← copy this to .env.dev and fill in values
├── src/
│   ├── core/                 ← config, API session, DB abstraction, constants
│   ├── fixtures/             ← reusable fixture factories
│   └── helpers/              ← assertions, API/DB helpers, data builders
├── tests/
│   ├── conftest.py           ← PROJECT WIRING (API + DB sessions) — edit this
│   ├── smoke/                ← health & connectivity tests
│   ├── integration/          ← API count vs DB count tests
│   └── e2e/<feature>/        ← CRUD workflow tests + data factories
├── docs/                     ← onboarding guides (start here)
├── ARCHITECTURE.md           ← system design and layer overview
├── Makefile                  ← make smoke / integration / e2e / verify
└── pytest.ini                ← markers, Allure output, pythonpath
```

---

## Configuration

`ConfigManager` loads `config/.env.{ENV}` (e.g. `config/.env.dev`) and merges shell env vars (shell always wins).

Key variables:

| Variable | Purpose |
|----------|---------|
| `ENV` | Selects env file (`dev`, `staging`) |
| `API_BASE_URL` | Required — primary API base URL |
| `API_AUTH_TYPE` | `none` / `bearer` / `basic` / `api_key` |
| `API_TOKEN` | Bearer token |
| `DB_ENGINE` | `mysql` / `postgresql` / `oracle` |
| `DATABASE_HOST/PORT/NAME/USER/PASSWORD` | DB connection |

Full variable reference: [docs/ENV_CONFIG.md](docs/ENV_CONFIG.md)

---

## Architecture

```
ConfigManager
    └── APISession / DatabaseConnection
            └── SharedTestResources (wired in tests/conftest.py)
                    └── test fixtures
                            └── tests
```

- `src/core/` is driver-agnostic — no DB drivers imported here
- `tests/conftest.py` is the **project customization boundary** — wire API and DB here
- `src/conftest.py` owns session-wide boilerplate — do not modify for project logic
- `state` fixture is function-scoped — use it only in e2e to pass IDs between steps
- `BaseFactory` produces plain dicts — no ORM, no DB writes — e2e only

Full architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Typical extension points

| Task | Where |
|------|-------|
| Override API / DB fixtures | `tests/conftest.py` |
| Add API endpoints and table names | `src/core/constants.py` |
| Implement a new DB engine | `src/project/db/<engine>_connection.py` |
| Add a new feature test area | `tests/e2e/<feature>/` + `tests/integration/` |
| Add a custom assertion | `src/helpers/assertions.py` |
| Add an extra API service session | `tests/conftest.py` via `make_api_fixture()` |

Step-by-step: [docs/EXTENDING.md](docs/EXTENDING.md)

---

## AI assistant context (Claude, Cursor, Codex)

| File | Purpose |
|------|---------|
| [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) | Entry point — imports all context files |
| [.claude/context/agents.md](.claude/context/agents.md) | Agent workflows and scope rules |
| [.claude/context/project.md](.claude/context/project.md) | Stack, layout, fork checklist |
| [.claude/context/testing.md](.claude/context/testing.md) | Test tiers, fixtures, helpers |
| [.claude/context/assertions.md](.claude/context/assertions.md) | Assertion helper API reference |
| [.claude/context/gotchas.md](.claude/context/gotchas.md) | Common mistakes to avoid |

Cursor rules: [.cursor/rules/project.mdc](.cursor/rules/project.mdc)

---

## Notes

- Never commit `config/.env*` files — they are gitignored
- Core DB layer has no driver imports — drivers live in `src/project/db/` only
- No unit tests in this repo — those belong in the backend app repository
- Configuration is env-variable driven via Pydantic BaseSettings
