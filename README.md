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
| 0 | [ONBOARDING.md](docs/ONBOARDING.md) | Prerequisites and access checklist — read before setup |
| 1 | [QUICK_START.md](docs/QUICK_START.md) | Set up the local environment and run your first smoke test |
| 2 | [ENV_CONFIG.md](docs/ENV_CONFIG.md) | Understand every config variable and how the loader resolves them |
| 3 | [API_SETUP.md](docs/API_SETUP.md) | Configure authentication and multi-service API sessions |
| 4 | [DATABASE_SETUP.md](docs/DATABASE_SETUP.md) | Wire the database connection |
| 5 | [TEST_PATTERNS.md](docs/TEST_PATTERNS.md) | Learn the smoke / integration / e2e test patterns with full examples |
| 6 | [EXTENDING.md](docs/EXTENDING.md) | Add tests for a new feature area from scratch |
| 7 | [DEBUGGING.md](docs/DEBUGGING.md) | Diagnose failures, read logs, common fixes |

Reference docs:
[BOILERPLATE_BOUNDARIES.md](docs/BOILERPLATE_BOUNDARIES.md) ·
[CI.md](docs/CI.md) · [RBAC_TESTING.md](docs/RBAC_TESTING.md) ·
[TEST_DESIGN_TEMPLATE.md](docs/TEST_DESIGN_TEMPLATE.md)

> **One-time GitHub Pages setup:** go to **Settings → Pages → Source** and select
> **GitHub Actions**. The Allure HTML report is published there automatically after every CI run.

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
```

### Run tests (same commands on every OS)

```bash
pytest tests/smoke -m "smoke and not db_required" -ra # API-only smoke checks
pytest tests/smoke -m smoke -ra                    # smoke including DB checks
pytest tests/integration -m integration -ra        # API count vs DB (requires DB config)
pytest tests/e2e -m e2e -ra                        # CRUD flows (requires DB config)

# All tests in order (smoke → integration → e2e)
pytest tests/smoke -m smoke -ra && pytest tests/integration -m integration -ra && pytest tests/e2e -m e2e -ra
```

---

> **CI — DB tests disabled:** The `db-tests` CI job (`RUN_DB_TESTS`) is currently disabled
> because the database is only reachable over the **LF VPN**. GitHub Actions runners cannot
> connect to it without VPN access. To run integration and e2e tiers, execute them locally with
> the VPN active:
> ```bash
> pytest tests/integration -m integration -ra
> pytest tests/e2e -m e2e -ra
> ```

---

## Test tiers

| Tier | Folder | Marker | Purpose |
|------|--------|--------|---------|
| Smoke | `tests/smoke/` | `@pytest.mark.smoke` | Health & connectivity — no DB required |
| Integration | `tests/integration/` | `@pytest.mark.integration` | API list count vs DB count (read-only, no factories) |
| E2E | `tests/e2e/<feature>/` | `@pytest.mark.e2e` | Feature CRUD; `tests/commons/data_builder/` payloads; `state` fixture |

---

## Project layout

```
pytest-automation-boilerplate/
├── config/
│   └── .env.example          ← copy this to .env.dev and fill in values
├── src/
│   ├── core/                 ← config, API session, DB abstraction, constants
│   ├── fixtures/             ← reusable fixture factories
│   └── helpers/              ← generic assertions, API/DB helpers, base data builder
├── api/                      ← typed API clients (BaseAPIClient subclasses), one per feature
├── tests/
│   ├── conftest.py           ← PROJECT WIRING (API + DB sessions) — edit this
│   ├── commons/              ← project-facing assertions, data builders, API schemas
│   ├── smoke/                ← health & connectivity tests
│   ├── integration/          ← API count vs DB count tests
│   └── e2e/<feature>/        ← CRUD workflow tests
├── docs/                     ← onboarding guides (start here)
├── ARCHITECTURE.md           ← system design and layer overview
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
| `API_AUTH_TYPE` | `none` / `bearer` / `basic` / `api_key` / `api_key_param` / `custom_headers` |
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
- `BaseFactory`/`ProjectBaseFactory` (`tests/commons/data_builder/`) produce plain dicts — no ORM, no DB writes — e2e only

Full architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Typical extension points

| Task | Where |
|------|-------|
| Override API / DB fixtures | `tests/conftest.py` |
| Add API endpoints and table names | `src/core/constants.py` |
| Implement a new DB engine | `src/project/db/<engine>_connection.py` |
| Add a new feature test area | `tests/e2e/<feature>/` + `tests/integration/` |
| Add a custom assertion | `tests/commons/assertions.py` (project-specific) or `src/helpers/assertions.py` (generic) |
| Add an extra API service session | `tests/conftest.py` via `make_api_fixture()` |

Step-by-step: [docs/EXTENDING.md](docs/EXTENDING.md)

---

## AI assistant context (Claude, Cursor, Codex)

| File | Purpose |
|------|---------|
| [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) | Entry point — imports all context files |
| [.claude/persona.md](.claude/persona.md) | The role/mindset the assistant should take in this repo |
| [.claude/context/agents.md](.claude/context/agents.md) | Agent workflows and scope rules |
| [.claude/context/project.md](.claude/context/project.md) | Stack, layout, fork checklist |
| [.claude/context/testing.md](.claude/context/testing.md) | Test tiers, fixtures, helpers |
| [.claude/context/assertions.md](.claude/context/assertions.md) | Assertion helper API reference |
| [.claude/context/gotchas.md](.claude/context/gotchas.md) | Common mistakes to avoid |
| [.claude/rules/*.md](.claude/rules/) | Enforceable Do/Don't standards (api, db, assertions, testing, new module) |
| [.claude/skills/*/SKILL.md](.claude/skills/) | Scaffolding automation for a new feature module |
| [.claude/agents/*.md](.claude/agents/) | Scoped subagents (schema investigation, test authoring, review, debugging) |

---

## Notes

- Never commit `config/.env*` files — they are gitignored
- Core DB layer has no driver imports — drivers live in `src/project/db/` only
- No unit tests in this repo — those belong in the backend app repository
- Configuration is env-variable driven via Pydantic BaseSettings
