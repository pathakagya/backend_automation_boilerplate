# Migration Guide

This project follows **semantic versioning** (MAJOR.MINOR.PATCH).

## Version policy

| Change type | Bump | Entry here? |
|---|---|---|
| Breaking fixture/API rename, removed helper, layout change | MAJOR | **Yes — required** |
| New feature, new adapter, new skill, new doc | MINOR | No |
| Internal refactor, performance fix, test fix | PATCH | No |

## Release process

1. Update `version` in `pyproject.toml`.
2. If MAJOR: add an entry below (see format).
3. Commit: `release: v<VERSION>`.
4. Tag: `git tag v<VERSION> && git push origin v<VERSION>`.

Forks that consume this template: merge from the upstream tag into a temporary
branch, resolve conflicts, run all tiers, then merge after QA approval.

---

## v1.0.0 — Baseline release (2026-10-14)

**Breaking changes:** None — this is the first versioned release.

### What's in this release

- Three-tier framework: smoke / integration / e2e
- DB-agnostic adapter layer: MySQL, PostgreSQL, Oracle (opt-in via `requirements-db.txt`)
- Provider-agnostic SMTP email notification after CI runs
- Allure HTML report published to GitHub Pages
- Claude Code AI tooling: 7 agents, 7 skills, 5 rule files
- Reference implementation: `tests/e2e/users/`

### Upgrading from pre-1.0 forks

No migration steps required. Review these files for new conventions your fork may not have:

- `requirements-db.txt` — DB drivers are now opt-in; remove `mysql-connector-python` from
  your `requirements.txt` if you added it there
- `scripts/generate_email_report.py` + `scripts/email_template.html` — email reporting
- `src/project/db/postgresql_connection.py` + `oracle_connection.py` — new adapters
- `.github/workflows/test.yml` — four jobs: api-smoke (matrix), db-tests, publish-report, notify
- `docs/CI.md` — full CI setup guide (Steps 1–4 + versioning)
