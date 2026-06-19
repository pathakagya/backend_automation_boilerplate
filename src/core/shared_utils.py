"""
Shared utilities for src/core modules.

Consolidates common functions used across api_session_manager, db_connection_manager, etc.
to avoid duplication and ensure consistency.
"""
from __future__ import annotations

import importlib
import json
from typing import Any


def get_allure_module() -> Any | None:
    """
    Safely import and return the allure module if available.

    Returns None if allure is not installed, allowing graceful fallback
    in non-Allure test environments.
    """
    try:
        return importlib.import_module("allure")
    except Exception:
        return None


def safe_json_serialize(obj: Any, indent: int = 2) -> str:
    """
    Serialize an object to JSON, converting non-serializable types to strings.

    Args:
        obj: Object to serialize (dict, list, or any JSON-serializable type).
        indent: JSON indentation level (default 2).

    Returns:
        JSON string.
    """
    return json.dumps(obj, indent=indent, default=str)


def attach_to_allure(
    content: str,
    name: str,
    attachment_type: str | None = None,
) -> None:
    """
    Attach content to the Allure report.

    Safe no-op if Allure is not available.

    Args:
        content: String content to attach.
        name: Display name in Allure report.
        attachment_type: Allure attachment type (e.g., "json", "text").
                        If None, auto-detects from content.
    """
    allure = get_allure_module()
    if allure is None:
        return

    if attachment_type is None:
        attachment_type = allure.attachment_type.TEXT

    allure.attach(content, name=name, attachment_type=attachment_type)


def attach_json_to_allure(data: Any, name: str) -> None:
    """
    Serialize data to JSON and attach to Allure report.

    Args:
        data: Object to serialize and attach.
        name: Display name in Allure report.
    """
    allure = get_allure_module()
    if allure is None:
        return

    content = safe_json_serialize(data)
    allure.attach(
        content,
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )
