"""
Common helper functions shared across helpers modules.

Consolidates utilities that appear in multiple helpers files to avoid duplication.
"""
from __future__ import annotations

import random
import string
import uuid
from typing import Any


# ---------------------------------------------------------------------------
# Random data generators (was duplicated in utils.py and data_builders.py)
# ---------------------------------------------------------------------------

def random_string(length: int = 8, prefix: str = "") -> str:
    """Generate a random alphanumeric string."""
    chars = string.ascii_lowercase + string.digits
    suffix = "".join(random.choices(chars, k=length))
    return f"{prefix}{suffix}"


def random_int(min_val: int = 1, max_val: int = 9999) -> int:
    """Generate a random integer within range."""
    return random.randint(min_val, max_val)


def random_email(domain: str = "test.example.com") -> str:
    """Generate a random email address."""
    return f"{random_string(8)}@{domain}"


def unique_id() -> str:
    """Generate a unique UUID string."""
    return str(uuid.uuid4())


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
