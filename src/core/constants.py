"""
Project-wide constants.

Centralise names that appear in multiple places so a single change
propagates everywhere (schema names, table names, HTTP paths, timeouts, etc.)

Projects should:
    1. Replace / extend these with their own values.
    2. Avoid hard-coding any of these strings in tests or helpers directly.
"""

# ---------------------------------------------------------------------------
# Database: schema / table name constants
# ---------------------------------------------------------------------------

class DBSchema:
    """Override with your actual schema names."""
    PRIMARY = "app_schema"


class DBTable:
    """Override with your actual table names."""
    USERS  = "users"


# ---------------------------------------------------------------------------
# API: path constants
# ---------------------------------------------------------------------------

class APIPath:
    """Relative URL paths for API endpoints."""
    USERS   = "/users"
    PEOPLE_FINDER = "/core/people-finder"
    CHANGE_LEAVE_ISSUER = "/core/leave-issuers/change-requests"
    NOTES = "/core/notes"

    
# ---------------------------------------------------------------------------
# Timeouts (seconds)
# ---------------------------------------------------------------------------

class Timeout:
    DEFAULT  = 30
    LONG     = 120
    DB_QUERY = 10


# ---------------------------------------------------------------------------
# HTTP Status Codes (convenience aliases)
# ---------------------------------------------------------------------------

class HTTPStatus:
    OK         = 200
    CREATED    = 201
    NO_CONTENT = 204
    BAD_REQUEST        = 400
    UNAUTHORIZED       = 401
    FORBIDDEN          = 403
    NOT_FOUND          = 404
    UNPROCESSABLE      = 422
    SERVER_ERROR       = 500


# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------

class Marker:
    INTEGRATION = "integration"
    E2E         = "e2e"
    SMOKE       = "smoke"


# ---------------------------------------------------------------------------
# Smoke test defaults
# ---------------------------------------------------------------------------

class SmokeModule:
    HEALTH = "health"
    DATABASE = "database"
    AUTH_SERVICE = "auth_service"
    CONFIG = "config"
    GENERIC_GET = "generic_get"


class SmokeTimeoutSeconds:
    """Per-module response-time thresholds used by smoke assertions."""
    BY_MODULE = {
        SmokeModule.HEALTH: 2.0,
        SmokeModule.DATABASE: 3.0,
        SmokeModule.AUTH_SERVICE: 3.0,
        SmokeModule.CONFIG: 2.0,
        SmokeModule.GENERIC_GET: 5.0,
    }
    DEFAULT = float(Timeout.DEFAULT)


class SmokeExpectedStatus:
    """Per-module expected HTTP status used by smoke assertions."""
    BY_MODULE = {
        SmokeModule.HEALTH: HTTPStatus.OK,
        SmokeModule.AUTH_SERVICE: HTTPStatus.OK,
        SmokeModule.GENERIC_GET: HTTPStatus.OK,
    }
    DEFAULT = HTTPStatus.OK


class SmokeDefaults:
    """Project-agnostic smoke defaults that can be overridden by env vars."""
    HEALTH_ENDPOINTS = ("/health", "/status")
    AUTH_HEALTH_PATH = "/auth/health"
    OPENAPI_PATH = "/openapi.json"
    REQUIRED_ENV_VARS = ("ENV", "API_BASE_URL")
    REQUIRED_SECRET_VARS = ("API_TOKEN", "DATABASE_PASSWORD")
    DB_MASTER_TABLES = ("user", "user_role")
