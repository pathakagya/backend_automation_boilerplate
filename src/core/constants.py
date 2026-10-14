"""
Project-wide constants.

Centralise names that appear in multiple places so a single change
propagates everywhere (schema names, table names, HTTP paths, timeouts, etc.)

Projects should:
    1. Keep generic defaults in the shared layer and put domain facts in the
       project's constants or registry module.
    2. Treat the Vyaguta constants below as reference-project facts, not
       required defaults for a new fork.
    3. Avoid hard-coding any of these strings in tests or helpers directly.
"""

# ---------------------------------------------------------------------------
# Database: schema / table name constants
# ---------------------------------------------------------------------------

class DBSchema:
    """Reference schema names; consuming projects should override these."""
    PRIMARY = "app_schema"


class DBTable:
    """
    Vyaguta reference project table names (confirmed live against vyaguta_qa DB).
    See docs/USERS_MODULE_TEST_DESIGN.md for the investigation behind these names.

    FORK INSTRUCTIONS: Replace the values below with your project's actual table
    names. Remove entries that don't apply and add your own.
    """
    USER = "user"
    DEPARTMENT = "department"
    DESIGNATION = "designation"
    AREA = "area"
    ENGAGEMENT_STATUS = "engagement_status"
    EMP_STATUS = "emp_status"
    EMP_STATUS_DETAILS = "emp_status_details"
    EMP_DESIGNATION_AREA = "emp_designation_area"
    EMP_LEAVE_ISSUERS = "emp_leave_issuers"
    EMP_TEAM_MANAGERS = "emp_team_managers"
    ROLES = "roles"
    ROLES_USERS = "roles_users"
    PERMISSIONS = "permissions"
    PERMISSIONS_ROLES = "permissions_roles"
    EMP_RESIGNATIONS = "emp_resignations"
    ATTENDANCE_LEAVE_CREDITS = "attendance_leave_credits"
    TEAMS_ALLOCATIONS = "teams_allocations"
    TEAMS_PROJECTS = "teams_projects"
    TEAMS_ROLES = "teams_roles"
    PULSE_NOTES = "pulse_notes"
    PULSE_PROBATIONS = "pulse_probations"


# ---------------------------------------------------------------------------
# API: path constants
# ---------------------------------------------------------------------------

class APIPath:
    """
    Vyaguta reference project API paths (confirmed against Core.postman_collection.json).
    The "/core" prefix is Vyaguta's service mount point — your project will differ.

    FORK INSTRUCTIONS: Replace all paths below with your project's actual API routes.
    Add new path constants here; never hardcode path strings in tests or clients.
    """
    PEOPLE_FINDER = "/core/people-finder"
    CHANGE_LEAVE_ISSUER = "/core/leave-issuers/change-requests"
    NOTES = "/core/notes"

    # --- Users module ---
    USERS = "/core/users"
    USER_BY_ID = "/core/users/{id}"
    USER_COUNT = "/core/users/count"
    USER_SUMMARY = "/core/users/summary"
    USER_DESIGNATION = "/core/users/{id}/designation"
    USER_ENGAGEMENT_STATUS = "/core/users/{id}/engagement-status"
    USER_EMPLOYEE_STATUS = "/core/users/{id}/employee-status"
    USER_TEAM_MANAGER = "/core/users/{id}/team-manager"
    USER_TEAM_MANAGER_HISTORY = "/core/users/{id}/team-manager-history"
    USER_LEAVE_ISSUER = "/core/users/{id}/leave-issuer"
    USER_ROLES = "/core/users/{id}/roles"
    USER_PERMISSIONS = "/core/users/{id}/permissions"
    USER_RELATIONS = "/core/users/{id}/relations"
    USER_ALL_RELATIONS = "/core/users/{id}/all-relations"
    USER_SKILLS_V2 = "/core/users/{id}/skills/v2"
    USER_SKILLS_V2_STATUS = "/core/users/{id}/skills/v2/{skill_id}/status"
    USER_RESIGNATIONS = "/core/users/{id}/resignations"
    USER_RESIGNATION_BY_ID = "/core/users/{id}/resignations/{resignation_id}"
    USER_UPLOAD = "/core/users/{id}/upload"
    USER_ACTIVATE = "/core/users/{id}/activate"
    USER_TEAM_SUMMARY = "/core/users/team-summary"
    USER_TEAM = "/core/users/{id}/team"


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
    """Convenience aliases for the most common HTTP status codes.
    For the full RFC set use: from http import HTTPStatus
    """
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
    RBAC        = "rbac"
    DB_REQUIRED = "db_required"


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
    """Project-agnostic smoke defaults that can be overridden by env vars.

    ``DB_MASTER_TABLES`` is intentionally empty for a new project. The
    Vyaguta reference suite supplies its own table list explicitly.
    """
    HEALTH_ENDPOINTS = ("/health", "/status")
    AUTH_HEALTH_PATH = "/auth/health"
    OPENAPI_PATH = "/openapi.json"
    REQUIRED_ENV_VARS = ("ENV", "API_BASE_URL")
    REQUIRED_SECRET_VARS = ()
    DB_MASTER_TABLES = ()


class VyagutaReference:
    """Names used by the working Vyaguta sample project.

    This registry exists to make the sample's domain assumptions visible. It
    must not be imported by generic helpers or copied into a new project
    without verifying the target API and database.
    """

    DB_MASTER_TABLES = (DBTable.USER, DBTable.ROLES)
    API_BASE_PATH = "/core"
