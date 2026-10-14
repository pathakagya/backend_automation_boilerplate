# Quick Start

> **New to this project?** Follow this doc first, then proceed in order:
> 0. [ONBOARDING.md](ONBOARDING.md) — prerequisites and access checklist (read this first)
> 1. **You are here** → QUICK_START.md (local setup + first run)
> 2. [ENV_CONFIG.md](ENV_CONFIG.md) — all configuration variables explained
> 3. [API_SETUP.md](API_SETUP.md) — wire your API connection
> 4. [DATABASE_SETUP.md](DATABASE_SETUP.md) — wire your database connection
> 5. [TEST_PATTERNS.md](TEST_PATTERNS.md) — how to write each test tier
> 6. [EXTENDING.md](EXTENDING.md) — add tests for a new feature
> 7. [DEBUGGING.md](DEBUGGING.md) — when something goes wrong

---

## Prerequisites

| Requirement | Minimum version | Check with |
|-------------|-----------------|------------|
| Python | 3.12+ | `python --version` |
| pip | any recent | `pip --version` |
| git | any | `git --version` |
| A running API (target system) | — | depends on your project |

---

## Step 1 — Clone and create a virtual environment

### macOS / Linux

```bash
git clone <repo-url>
cd pytest-automation-boilerplate

python -m venv venv
source venv/bin/activate
```

### Windows

```bash
git clone <repo-url>
cd pytest-automation-boilerplate

python -m venv venv
venv\Scripts\activate
```

---

## Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs pytest, requests, Pydantic, Allure adapter, Faker, and all other required packages.

> **DB driver not included.** `requirements.txt` installs no database driver — drivers are kept separate so you only install the one your project needs. If you plan to run integration or e2e tests:
>
> 1. Ask your team lead which engine and version the team uses (e.g. `mysql-connector-python==9.0.0`, `psycopg2-binary==2.9.9`, or `oracledb==2.0.0`).
> 2. Open `requirements-db.txt` at the repo root, uncomment the matching line (update the version if your team uses a pinned one), and run:
>
> ```bash
> pip install -r requirements-db.txt
> ```
>
> Skipping this step is fine if you only plan to run smoke tests — those need no DB connection.

---

## Step 3 — Create your config file

### macOS / Linux

```bash
cp config/.env.example config/.env.dev
```

### Windows

```bash
copy config\.env.example config\.env.dev
```

> **Important:** The `.env.example` file contains placeholder values (`https://api.example.com`, `CHANGE_ME`). Tests that call the API will fail with a `ConnectionError` until you replace these with real values. If you don't have real values yet, you can still validate the framework setup by running only the env-var smoke test: `pytest tests/smoke -m smoke -k "test_required_env_vars" -ra`.

Open `config/.env.dev` in your text editor (Notepad, VS Code, or your IDE) and fill in the minimum required values:

```ini
# Which environment this file is for
ENV=dev

# The base URL of the API under test (required)
API_BASE_URL=https://your-api.example.com

# Authentication — pick one strategy (see docs/API_SETUP.md for details)
API_AUTH_TYPE=none          # none | bearer | basic | api_key | api_key_param

# Database engine (required only if you run integration/e2e tests)
DB_ENGINE=mysql             # mysql | postgresql | oracle

# Database connection (required only if DB_ENGINE is set)
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=your_db
DATABASE_USER=your_user
DATABASE_PASSWORD=your_password
```

> **Tip:** Env vars always override file values. You can `export API_BASE_URL=...` in your shell instead of editing the file. See [ENV_CONFIG.md](ENV_CONFIG.md) for the complete variable reference.

---

## Step 4 — Export the environment selector

### macOS / Linux

```bash
export ENV=dev
```

### Windows

```bash
set ENV=dev
```

This tells `ConfigManager` to load `config/.env.dev`. Run this in every new shell session.

> **Windows Tip:** Environment variables set with `set` persist only in the current terminal session. To set them permanently, use System Environment Variables in Settings.

---

## Step 5 — Run smoke tests

Same command on every OS:

```bash
pytest tests/smoke -m smoke -ra
```

**What you should see:**

The smoke suite collects tests from `tests/smoke/test_smoke.py` and any project-specific
subfolders (e.g. `tests/smoke/vyaguta/`). The Vyaguta reference tests will fail on a new
project — exclude them with `-k "not Vyaguta"` until you have your own smoke tests:

```bash
pytest tests/smoke -m smoke -k "not Vyaguta" -ra
```

Tests that call the API require a configured `API_BASE_URL`. With placeholder values you will
see `ConnectionError` failures — that is expected until you fill in real credentials.

The env-var check test (`test_required_env_vars`) should always pass and confirms the framework
is wired up correctly regardless of API access.

If all tests you expect to pass do pass, your environment is set up correctly.

---

## Step 6 — Run the full suite (optional)

Same commands on every OS. Run all tests in sequence:

```bash
pytest tests/smoke -m smoke -ra && pytest tests/integration -m integration -ra && pytest tests/e2e -m e2e -ra
```

Or run each tier individually:

```bash
pytest tests/smoke -m smoke -ra                 # fast health/connectivity checks
pytest tests/integration -m integration -ra     # API count vs DB (requires DB config)
pytest tests/e2e -m e2e -ra                     # CRUD flows (requires DB config)
```

> Integration and E2E tests will be **skipped** (not failed) if DB config is missing. This is intentional — smoke tests can still validate API connectivity alone.

---

## Step 7 — View the Allure report (optional)

Tests automatically write results to `allure-results/`. To view the HTML report:

```bash
# Install Allure CLI if you haven't
# brew install allure   (macOS)
# or follow https://docs.qameta.io/allure/#_installing_a_commandline

allure serve allure-results
```

---

## Project layout at a glance

```
pytest-automation-boilerplate/
├── config/
│   ├── .env.example          ← copy this to .env.dev, fill in values
│   └── .env.dev              ← your local config (gitignored)
├── src/
│   ├── core/                 ← config, API session, DB abstraction, constants
│   ├── fixtures/             ← reusable fixture factories
│   └── helpers/              ← assertions, API/DB helpers, data builders
├── tests/
│   ├── conftest.py           ← PROJECT WIRING (API + DB sessions) — edit this
│   ├── smoke/                ← health & connectivity tests
│   ├── integration/          ← API count vs DB count tests
│   └── e2e/<feature>/        ← CRUD workflow tests
├── docs/                     ← you are here
└── pytest.ini                ← markers, Allure output, pythonpath
```

---

## What to do before writing your first test

The full checklist — fixture wiring, constants, and (if needed) a new DB driver — is in
[ONBOARDING.md § "What minimal changes to go live actually means"](ONBOARDING.md#4-what-minimal-changes-to-go-live-actually-means).
Once that's done, read [TEST_PATTERNS.md](TEST_PATTERNS.md) to know which folder your first test belongs in.

---

## Next step

→ [ENV_CONFIG.md](ENV_CONFIG.md) — understand every config variable and how the loader resolves them
