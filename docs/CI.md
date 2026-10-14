# CI and release governance

> **Setting up CI for the first time?** Read this file top-to-bottom — it covers every secret,
> variable, and one-time configuration step in the order you'll need them.

---

## Workflow overview

The default workflow (`.github/workflows/test.yml`) has four jobs that run in sequence:

```
api-smoke ──┐
            ├──► publish-report ──► notify
db-tests  ──┘
```

| Job | When it runs | What it does |
|---|---|---|
| `api-smoke` | Every push / PR | Validates Python sources, collects and runs API-only smoke tests |
| `db-tests` | Only when `RUN_DB_TESTS=true` | Runs integration and e2e tiers against a real database |
| `publish-report` | Always, after both test jobs | Generates Allure HTML report and deploys to GitHub Pages |
| `notify` | Always, after `publish-report` | Sends an HTML email with test results and a link to the report |

Jobs marked "always" run even when an earlier job fails — you still get a report and notification
on a broken build.

---

## Step 1 — API secrets (required for smoke tests to run)

Set these in **Settings → Secrets and variables → Actions → Secrets**:

| Secret | Required | Value |
|---|---|---|
| `API_BASE_URL` | Yes — to run tests | Base URL of the API under test (e.g. `https://api.staging.example.com`) |
| `API_TOKEN` | Only if auth is `bearer` | Bearer token for the API session |
| `API_USERNAME` | Only if auth is `basic` | Username for basic auth |
| `API_PASSWORD` | Only if auth is `basic` | Password for basic auth |

Set these in **Settings → Secrets and variables → Actions → Variables**:

| Variable | Default | Value |
|---|---|---|
| `API_AUTH_TYPE` | `none` | Auth type: `none` / `bearer` / `basic` / `api_key` / `api_key_param` / `custom_headers` |

> **Without `API_BASE_URL`:** the smoke test step is skipped gracefully — CI still passes
> (validation and collection still run). This is intentional so the workflow works in forks
> that haven't wired up credentials yet.

---

## Step 2 — Database secrets (required for integration and e2e)

DB-backed jobs only run when the `RUN_DB_TESTS` variable is set to `true`. Leave it unset to
skip them (e.g. on a PR where no DB is available).

Set in **Settings → Secrets and variables → Actions → Variables**:

| Variable | Value |
|---|---|
| `RUN_DB_TESTS` | `true` to enable; omit or set to anything else to skip |
| `DB_ENGINE` | `mysql` / `postgresql` / `oracle` |

Set in **Settings → Secrets and variables → Actions → Secrets**:

| Secret | Value |
|---|---|
| `DB_ADAPTER_CLASS` | Optional — fully qualified class path override (e.g. `project.db.custom.MyConnection`) |
| `DATABASE_HOST` | DB host |
| `DATABASE_PORT` | DB port |
| `DATABASE_NAME` | Database / schema name |
| `DATABASE_USER` | DB user |
| `DATABASE_PASSWORD` | DB password |

---

## Step 3 — GitHub Pages (one-time repo setup)

The `publish-report` job deploys the Allure HTML report to GitHub Pages after every run.

1. Go to **Settings → Pages → Source** and select **GitHub Actions**.
2. The report URL will be: `https://<org>.github.io/<repo>/`

> **Private repos:** GitHub Pages requires GitHub Team or Enterprise for private repositories.
> If Pages isn't available, the publish job will fail — set its `if:` condition to
> `always() && vars.PUBLISH_REPORT != 'false'` and skip it with a variable to opt out cleanly.

---

## Step 4 — Email notification (optional)

The `notify` job sends an HTML email with a pass/fail summary, suite breakdown, failed test
names with error snippets, and a link to the full Allure report.

**It is completely optional.** The job is skipped silently when `NOTIFY_EMAIL` is not set —
no CI failure, no noise.

### Secrets and variables

Set in **Settings → Secrets and variables → Actions**:

| Name | Kind | Value |
|---|---|---|
| `MAIL_USERNAME` | Secret | Sending email address (e.g. `yourteam.ci@gmail.com`) |
| `MAIL_PASSWORD` | Secret | Gmail App Password — see setup below |
| `NOTIFY_EMAIL` | Variable | Recipient address(es), comma-separated (e.g. `qa@example.com,lead@example.com`) |
| `MAIL_SMTP_HOST` | Variable (optional) | SMTP host — default: `smtp.gmail.com` |
| `MAIL_SMTP_PORT` | Variable (optional) | SMTP port — default: `465` |

### Gmail App Password setup (~5 min, one-time)

Gmail is the recommended default — free, works in any GitHub repo, no OAuth complexity.

1. Create (or designate) a shared Gmail account for CI: e.g. `yourteam.ci@gmail.com`.
2. Enable **2-Step Verification** on that Google account (required before App Passwords work).
3. Go to **Google Account → Security → App passwords**.
4. Create a new App Password labelled `GitHub CI`. Google generates a 16-character password.
5. Store the 16-character password as `MAIL_PASSWORD` (GitHub Secret).
6. Store the Gmail address as `MAIL_USERNAME` (GitHub Secret).

**Using Office 365 or another SMTP provider?** Set `MAIL_SMTP_HOST` and `MAIL_SMTP_PORT` to
your provider's values. The action speaks plain SMTP — any server works.

### How the email report is generated

`scripts/generate_email_report.py` reads the raw `allure-results/*.json` files (no Allure CLI
needed in this step). If Allure results are absent it falls back to parsing `junit-smoke.xml`.
The HTML body is rendered from `scripts/email_template.html` (Jinja2) — edit that file freely
to match your team's branding.

---

## Secrets security

- All credentials are supplied via GitHub's encrypted secret store — never committed to `.env`
  files or printed in logs.
- `DatabaseConnection` redacts fields named `password`, `token`, `secret`, `api_key`, and
  `authorization` before attaching query results to Allure reports.
- Review JUnit XML and Allure artifacts for sensitive data before sharing them outside CI.

---

## Versioning and releases

This boilerplate uses **semantic versioning** (MAJOR.MINOR.PATCH). The current version is in
`pyproject.toml` under `[project]`. Breaking changes (fixture renames, removed helpers, layout
shifts) require a MAJOR bump **and** an entry in `MIGRATION.md`. New features and adapters are
MINOR; internal fixes are PATCH.

**Tag convention:**

```bash
# After updating pyproject.toml and committing
git tag v1.0.0
git push origin v1.0.0
```

See `MIGRATION.md` for upgrade notes and the full version policy.

---

## Fork releases

Projects consume this repository as a template fork. When the shared template changes:

1. Read `MIGRATION.md` and this changelog for breaking changes.
2. Merge the shared changes into a temporary branch.
3. Run API-only smoke and collection checks.
4. Run the project's DB adapter health check and DB-backed tiers.
5. Review method documentation and project boundary changes.
6. Merge after QA approval.

Vendor drivers remain project-owned dependencies and must not be added to the shared core
merely to support one consumer.

