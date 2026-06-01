# Environment and Configuration

> **Onboarding step 2 of 7** | Prev: [QUICK_START.md](QUICK_START.md) | Next: [API_SETUP.md](API_SETUP.md)

---

## How configuration is loaded

```
ENV=dev
   │
   ▼
config/.env.dev          ← loaded first (file-based values)
   │
   ▼
Shell environment vars   ← always override file values
   │
   ▼
ConfigManager            ← single source of truth in tests
```

`ConfigManager` uses Pydantic `BaseSettings` under the hood. It reads `config/.env.{ENV}` and then merges in any env vars that are already set in the shell — shell values win.

---

## ENV file resolution

| `ENV` value | File loaded | Fallback |
|-------------|-------------|---------|
| `dev` | `config/.env.dev` | `config/.env` |
| `staging` | `config/.env.staging` | `config/.env` |
| _(unset)_ | `config/.env` | — |

**Always export `ENV` before running tests:**

```bash
export ENV=dev
make smoke
```

If the selected file does not exist and `config/.env` also doesn't exist, `ConfigManager` falls back to pure environment variables.

---

## Complete variable reference

### API connection

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | **Yes** | `https://api.example.com` | Base URL of the system under test |
| `API_AUTH_TYPE` | No | `bearer` | Auth strategy: `none`, `bearer`, `basic`, `api_key`, `api_key_param`, `custom_headers` |
| `API_TOKEN` | When `bearer` | `eyJhbG...` | Bearer token |
| `API_USERNAME` | When `basic` | `testuser` | Basic auth username |
| `API_PASSWORD` | When `basic` | `secret` | Basic auth password |
| `API_KEY` | When `api_key` | `abc123` | API key value |
| `API_KEY_HEADER` | When `api_key` | `X-API-Key` | Header name for the key |
| `API_TIMEOUT` | No | `30` | Request timeout in seconds (default: 30) |

> See [API_SETUP.md](API_SETUP.md) for full auth strategy examples.

### Optional second service

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `AUTH_SERVICE_BASE_URL` | No | `https://auth.example.com` | Base URL for a second service (e.g. a dedicated auth service) |

### Database connection

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `DB_ENGINE` | For DB tests | `mysql` | `mysql`, `postgresql`, `oracle` |
| `DATABASE_HOST` | For DB tests | `localhost` | Database host |
| `DATABASE_PORT` | For DB tests | `3306` | Database port |
| `DATABASE_NAME` | For DB tests | `app_db` | Schema / database name |
| `DATABASE_USER` | For DB tests | `qa_user` | Database username |
| `DATABASE_PASSWORD` | For DB tests | `secret` | Database password |

> If DB vars are missing or incomplete, all tests that require `db_connection` are **skipped** (not failed). See [DATABASE_SETUP.md](DATABASE_SETUP.md).

### Smoke test overrides (optional)

These override the default values in `src/core/constants.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SMOKE_HEALTH_ENDPOINTS` | `/health,/status` | Comma-separated paths to hit for health checks |
| `SMOKE_AUTH_HEALTH_PATH` | `/auth/health` | Health endpoint for the auth service |
| `SMOKE_OPENAPI_PATH` | `/openapi.json` | OpenAPI spec path |

---

## Variable naming convention

Variables follow the pattern `SECTION_KEY`, which maps to `section.key` in `ConfigManager` accessors:

| Env var | ConfigManager accessor |
|---------|----------------------|
| `API_BASE_URL` | `config.get_api_config()["base_url"]` |
| `DB_ENGINE` | `config.get_database_config()["engine"]` |
| `DATABASE_HOST` | `config.get_database_config()["host"]` |

---

## Using ConfigManager in tests

`config` is a session-scoped fixture provided by `src/conftest.py`. You do not need to instantiate it yourself.

```python
def test_something(config):
    # Get a specific value (raises if missing)
    base_url = config.require("api", "base_url")

    # Get the full API config dict
    api_cfg = config.get_api_config()
    # {"base_url": "...", "auth_type": "bearer", "token": "..."}

    # Get the full DB config dict
    db_cfg = config.get_database_config()
    # {"engine": "mysql", "host": "...", "port": "3306", ...}
```

---

## Example `.env.dev` file

```ini
ENV=dev

# API
API_BASE_URL=https://api.dev.example.com
API_AUTH_TYPE=bearer
API_TOKEN=your-dev-token-here

# Database
DB_ENGINE=mysql
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=app_db
DATABASE_USER=qa_user
DATABASE_PASSWORD=qa_password
```

---

## CI / GitHub Actions

In CI, set variables as repository secrets and reference them in your workflow:

```yaml
env:
  ENV: staging
  API_BASE_URL: ${{ secrets.API_BASE_URL }}
  API_TOKEN: ${{ secrets.API_TOKEN }}
  DATABASE_HOST: ${{ secrets.DATABASE_HOST }}
  DATABASE_PASSWORD: ${{ secrets.DATABASE_PASSWORD }}
```

Never commit `.env.dev` or `.env.staging` files — they are gitignored.

---

## Next step

→ [API_SETUP.md](API_SETUP.md) — configure authentication and multi-service API sessions
