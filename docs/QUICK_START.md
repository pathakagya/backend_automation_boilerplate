# Quick Start

> **New to this project?** Follow this doc first, then proceed in order:
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

```bash
git clone <repo-url>
cd pytest-automation-boilerplate

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```

---

## Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs pytest, requests, Pydantic, Allure adapter, Faker, and all other required packages.

---

## Step 3 — Create your config file

```bash
cp config/.env.example config/.env.dev
```

Open `config/.env.dev` and fill in the minimum required values:

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

```bash
export ENV=dev
```

This tells `ConfigManager` to load `config/.env.dev`. Run this in every new shell session, or add it to your shell profile.

---

## Step 5 — Run smoke tests

```bash
make smoke
# equivalent: pytest tests/smoke -m smoke
```

**What you should see:**

```
collected 5 items

tests/smoke/test_smoke.py::TestSmoke::test_health_check_endpoints PASSED
tests/smoke/test_smoke.py::TestSmoke::test_required_env_vars PASSED
...

5 passed in 3.21s
```

If smoke tests pass, your environment is set up correctly.

---

## Step 6 — Run the full suite (optional)

```bash
make verify          # runs smoke → integration → e2e in order
```

Or run each tier individually:

```bash
make smoke           # fast health/connectivity checks
make integration     # API count vs DB (requires DB config)
make e2e             # CRUD flows (requires DB config)
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
├── Makefile                  ← make smoke / integration / e2e / verify
└── pytest.ini                ← markers, Allure output, pythonpath
```

---

## What to do before writing your first test

1. Fill in `tests/conftest.py` with real API and DB fixture wiring → see [API_SETUP.md](API_SETUP.md) and [DATABASE_SETUP.md](DATABASE_SETUP.md)
2. Update `src/core/constants.py` with your API paths, schema names, and table names
3. Run `make smoke` to confirm connectivity
4. Read [TEST_PATTERNS.md](TEST_PATTERNS.md) to understand which folder your test belongs in

---

## Next step

→ [ENV_CONFIG.md](ENV_CONFIG.md) — understand every config variable and how the loader resolves them
