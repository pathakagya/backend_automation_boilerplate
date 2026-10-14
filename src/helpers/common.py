"""
Common helper functions shared across helpers modules.

Consolidates utilities that appear in multiple helpers files to avoid duplication.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Object field access helper (was duplicated in assertions.py and db_helper.py)
# ---------------------------------------------------------------------------

def get_field(obj: Any, field_name: str, default: Any = None) -> Any:
    """
    Get a field value from a dict or object.

    Handles both dict-like objects (using .get()) and objects with attributes (using getattr()).

    Args:
        obj: Dictionary, namedtuple, or object with attributes.
        field_name: Field/attribute name to retrieve.
        default: Default value if field is not found.

    Returns:
        The field value, or default if not found.
    """
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    else:
        return getattr(obj, field_name, default)


# ---------------------------------------------------------------------------
# Database helper utilities
# ---------------------------------------------------------------------------

def qualify_table(table: str, schema: str = "") -> str:
    """
    Qualify a table name with an optional schema prefix.

    Args:
        table: Table name.
        schema: Optional schema name (e.g., "app_schema").

    Returns:
        Schema-qualified table name, or just table if schema is empty.

    Example:
        qualify_table("users")                    # "users"
        qualify_table("users", "app_schema")      # "app_schema.users"
    """
    return f"{schema}.{table}" if schema else table


def placeholder(paramstyle: str, index: int) -> str:
    """
    Build a single SQL bind-parameter placeholder for the given PEP 249 paramstyle.

    Args:
        paramstyle: A DatabaseConnection subclass's declared paramstyle
            ("qmark" | "numeric" | "named" | "format" | "pyformat").
        index: 1-based position of this parameter (used only by "numeric").

    Returns:
        "%s" for "format"/"pyformat" (e.g. mysql-connector-python, psycopg2 positional),
        "?" for "qmark" (e.g. sqlite3, pyodbc),
        ":{index}" for "numeric" (e.g. cx_Oracle/oracledb positional binds).

    Never hardcode a placeholder style in a query builder — use this so the same helper
    works against whichever engine's DatabaseConnection subclass is configured.
    """
    if paramstyle == "qmark":
        return "?"
    if paramstyle == "numeric":
        return f":{index}"
    return "%s"  # format / pyformat


def parse_json_safe(obj: Any) -> dict | list | None:
    """
    Safely parse JSON from a response or string.

    Returns None if parsing fails.

    Args:
        obj: JSON-like object or string.

    Returns:
        Parsed JSON as dict/list, or None on error.
    """
    try:
        if hasattr(obj, "json"):
            return obj.json()
        if isinstance(obj, str):
            import json
            return json.loads(obj)
        return obj
    except Exception:
        return None
