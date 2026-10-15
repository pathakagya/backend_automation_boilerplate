# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@.claude/persona.md
@.claude/context/agents.md
@.claude/context/project.md
@.claude/context/testing.md
@.claude/context/assertions.md
@.claude/context/gotchas.md

---

## Rules & skills

Enforceable Do/Don't standards live in `.claude/rules/*.md` (read as needed, not auto-imported):
`api-standards.md`, `assertions.md`, `testing.md`, `db-standards.md`, `new-module.md`. The
`.claude/context/*.md` files above are the reference/lookup tables; `.claude/rules/*.md` are the
rulebook.

Scaffolding a new module is automated by `.claude/skills/*/SKILL.md` — start with
`setup-test-module` (orchestrates the rest: `generate-api-client`, `generate-conftest`,
`generate-data-builder` + its field-classification `CHECKLIST.md`, `generate-test-file`).
`e2e-tests-generator` is a separate, research-gated skill for writing new e2e coverage without
guessing DB/API facts.
`requirements-to-tests` is the intake gate: Jira/spec evidence → scenario matrix → QA approval
before the generation skills are used.

**`tests/e2e/users/`** is a real, worked reference implementation (built against an actual
internal HR system) kept intentionally for other QA engineers to study the patterns — read it
for structure and conventions, but do not treat it as a copy-paste template for a new module;
follow `.claude/rules/new-module.md` instead.

---

## Agents

Prefer the scoped subagent below over doing the work inline — each owns one job and reads only the context files it needs.

| Task | Agent |
|---|---|
| Table/column unknown, schema investigation | `db-schema-investigator` |
| Test needs pre-existing DB rows across related tables | `data-seeder` |
| Deciding test tier, folder, or fixture placement | `test-architect` |
| Writing or fixing a smoke/integration/e2e test | `backend-test-engineer` |
| Reviewing for missing edge cases/coverage gaps | `quality-advocate` |
| A test fails and the cause isn't obvious | `debugging-specialist` |

For SOLID/DRY/duplication review of finished code, use the `/simplify` skill (and `/code-review` for correctness bugs). There is deliberately no `design-reviewer` agent: it was removed because it duplicated those two skills, and having both left it unclear which one to invoke.

Definitions: `.claude/agents/*.md`. No `business-analyst` agent yet — add one per fork once the project has real requirements docs (Confluence/Jira) to read.

---

## Commands

### Setup

macOS/Linux:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env.dev   # fill in values
export ENV=dev
```

Windows:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy config\.env.example config\.env.dev   # fill in values
set ENV=dev
```

### Run tests (same commands on every OS)

```bash
pytest tests/smoke -m smoke -ra                    # fast health/connectivity checks
pytest tests/integration -m integration -ra        # API count vs DB (requires DB config)
pytest tests/e2e -m e2e -ra                        # CRUD flows (requires DB config)

# All three in order
pytest tests/smoke -m smoke -ra && pytest tests/integration -m integration -ra && pytest tests/e2e -m e2e -ra

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
| `API_AUTH_TYPE` | `none` / `bearer` / `basic` / `api_key` / `api_key_param` / `custom_headers` |
| `API_TOKEN` | Bearer token (when `API_AUTH_TYPE=bearer`) |
| `API_USERNAME` / `API_PASSWORD` | Basic auth credentials |
| `DB_ENGINE` | `mysql` / `postgresql` / `oracle` |
| `DATABASE_HOST` / `PORT` / `NAME` / `USER` / `PASSWORD` | DB connection |
| `AUTH_SERVICE_BASE_URL` | Optional second service session |

Full variable reference: `docs/ENV_CONFIG.md`.

## Architecture flow

Config (`ConfigManager`) → `APISession` / `DatabaseConnection` → `SharedTestResources` (wired in `tests/conftest.py`) → test fixtures → tests.

- `src/core/` is driver-agnostic; DB drivers live in `src/project/db/` only.
- `tests/conftest.py` dynamically imports the right DB class from `engine_map` based on `DB_ENGINE`.
- `src/conftest.py` owns session-wide boilerplate (`config`, `run_prefix`, `state`); never modify it for project-specific logic.
- `state` fixture (`StateManager`) is function-scoped; use it in e2e only to pass IDs between steps.
- `BaseFactory`/`ProjectBaseFactory` produce plain dicts — no ORM, no DB writes — and belong only in `tests/commons/data_builder/<feature>.py`, used only from `tests/e2e/`.

