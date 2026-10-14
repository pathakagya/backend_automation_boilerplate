# Onboarding — Prerequisites

> **Read this before [QUICK_START.md](QUICK_START.md).** This page is not a setup step — nothing
> here involves running a command. It's the checklist a QA lead hands a junior QA (or a new
> fork) before they touch the framework: what they should already know, and what they need to
> get from the target project first. Skipping it doesn't block you, but every item below is
> something people commonly discover the hard way, mid-test-writing.

---

## 1. Knowledge prerequisites

| Area | What you need | Why |
|------|---------------|-----|
| Python + pytest | Fixtures, markers, `conftest.py` resolution order, parametrize | The whole framework is fixture composition — if fixtures are unfamiliar, start there before writing a test |
| HTTP / REST | Status codes, JSON bodies, auth headers (bearer/basic/api key) | You'll write typed `BaseAPIClient` subclasses, not raw `requests` calls — see `.claude/rules/api-standards.md` |
| SQL basics | `SELECT` / `COUNT` / `WHERE`, reading a schema/ERD | You read query results (`fetch_row`, `fetch_all`); you don't hand-write engine-specific SQL — that's what `helpers/db_helper.py` exists to avoid |
| Git | Branching, PRs | This repo is a **template** — each project forks it |

If any of these are shaky, pair on one existing test first (`tests/e2e/users/` is a real, worked
reference — see [TEST_PATTERNS.md](TEST_PATTERNS.md)) rather than starting from a blank file.

---

## 2. Access & information checklist — get this from the target project

Gather all of this *before* writing the first test. Each row maps to a concrete config value or
constant you'll fill in during setup.

| # | What to get | Feeds into |
|---|--------------|-----------|
| 1 | API base URL + auth mechanism (`none` / `bearer` / `basic` / `api_key` / `api_key_param` / `custom_headers`) | `config/.env.dev` → [API_SETUP.md](API_SETUP.md) |
| 2 | DB engine (MySQL / PostgreSQL / Oracle / other) + host, port, name, user, password | `config/.env.dev` → [DATABASE_SETUP.md](DATABASE_SETUP.md) |
| 3 | Whether that DB engine already has a driver in `src/project/db/` | See **"If your DB engine isn't supported yet"** below |
| 4 | API contract — OpenAPI/Swagger spec, Postman collection, or at minimum an endpoint + response-shape list | `src/core/constants.py::APIPath`, `tests/commons/api_schemas/` |
| 5 | DB schema/ERD — table + column names, FK relationships, which tables are master/reference data | `src/core/constants.py::DBTable`, `SmokeDefaults.DB_MASTER_TABLES` |
| 6 | A reachable dev/staging environment for both the API and the DB | Everything — this framework runs against a real API + DB, there is no mocking layer |
| 7 | GitHub repo admin access (to add secrets/variables and enable Pages) | [CI.md](CI.md) — required to activate smoke runs, DB tests, Allure Pages, and email notification |

### If your DB engine isn't supported yet

Check `TestResourcesManager.DB_ENGINE_MAP` in `src/core/test_resources.py`. The boilerplate
ships with reference adapters for MySQL, PostgreSQL, and Oracle in `src/project/db/`. Adding a
new engine only requires creating a new `DatabaseConnection` subclass there — nothing in
`src/core/` or any test file needs to change. Full steps:
[DATABASE_SETUP.md § "Adding a new database engine"](DATABASE_SETUP.md#adding-a-new-database-engine).

---

## 3. Framework orientation — read before writing code

| Read | For |
|------|-----|
| `CLAUDE.md` + `.claude/context/*.md` | Stack, layout, fixture hierarchy, assertions API, common gotchas |
| `.claude/rules/*.md` | Enforceable Do/Don'ts — `db-standards.md` matters most for a new DB engine, `testing.md` for tier placement |
| `tests/e2e/users/` | A real, worked reference implementation — study the patterns, don't copy-paste it as a template |
| [TEST_PATTERNS.md](TEST_PATTERNS.md) | The smoke / integration / e2e tier boundary — the #1 thing juniors get wrong early |

---

## 4. What "minimal changes to go live" actually means

Once the checklist above is filled in, wiring a new project takes exactly these touches — and
**nothing else**:

- `config/.env.dev` — your values
- `tests/conftest.py` — API + DB fixture wiring
- `src/core/constants.py` — your endpoint paths and table/column names
- `src/project/db/<engine>_connection.py` — **only** if your DB engine isn't MySQL

Nothing in `src/core/`, `src/helpers/`, or any existing test file should need to change. If a
task seems to require editing those, stop and re-check the tier/fixture boundary in
[TEST_PATTERNS.md](TEST_PATTERNS.md) first — it usually means the change belongs somewhere else.

---

## Next steps

→ [QUICK_START.md](QUICK_START.md) — local environment setup and your first smoke test run

→ [CI.md](CI.md) — wiring up GitHub Actions: API secrets, DB secrets, GitHub Pages, and email
notification (four numbered steps, do them in order)
