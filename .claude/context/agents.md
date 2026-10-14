# Agent instructions

Pytest automation boilerplate for backend API and database validation. Keep changes scoped; match existing patterns.

## Context files (read as needed)

| File | When to read |
|------|--------------|
| `project.md` | Stack, layout, env setup, first-time fork steps |
| `testing.md` | Test tiers, which folder to use, fixtures, helpers |
| `assertions.md` | `tests.commons.assertions` full API reference |
| `gotchas.md` | Repeated mistakes — check before writing any test |

Enforceable Do/Don't standards: `.claude/rules/*.md`. Scaffolding: `.claude/skills/*/SKILL.md`.

## Definition of done

- [ ] Correct folder and marker — see `testing.md` for tier rules
- [ ] No secrets in git; no DB drivers in `src/core/`
- [ ] Uses `tests.commons.assertions` (see `assertions.md`)
- [ ] Integration: no `BaseFactory`; E2E: factories only under `tests/commons/data_builder/`
- [ ] `pytest` passes for all touched tiers (smoke/integration/e2e as applicable)

## Scope of changes

| What | Where |
|------|-------|
| Generic helpers, config, session (project-agnostic, ships with the boilerplate) | `src/core/`, `src/fixtures/`, `src/helpers/` |
| Project-facing shared test modules (assertions, data builders, schemas) | `tests/commons/` |
| Project wiring (API + DB sessions) | `tests/conftest.py` |
| Smoke tests | `tests/smoke/` |
| Integration tests (count parity) | `tests/integration/` — no factories |
| E2E tests + typed API clients | `tests/e2e/<feature>/`, `api/<feature>_client.py` — factories live in `tests/commons/data_builder/` |

## Deep references

- `ARCHITECTURE.md`, `docs/TEST_PATTERNS.md`, `docs/EXTENDING.md`
- Fork steps → `project.md` · Which folder → `testing.md` · Run commands → `CLAUDE.md`

## Do not

- Commit secrets or `config/.env*`
- Import DB drivers into `src/core/`
- Add drive-by refactors outside the requested scope
- Duplicate `ARCHITECTURE.md` / `docs/` into context files — link instead
- Add unit tests or `tests/unit/` (backend app repo owns those)
