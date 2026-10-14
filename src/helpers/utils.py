"""
General utilities used across tests and helpers.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def today_str(fmt: str = "%Y-%m-%d") -> str:
    """Return today's local date formatted with ``fmt``."""
    return date.today().strftime(fmt)


def now_utc_str(fmt: str = "%Y-%m-%dT%H:%M:%SZ") -> str:
    """Return the current UTC timestamp formatted with ``fmt``."""
    return datetime.now(tz=timezone.utc).strftime(fmt)


def format_date(dt: date | datetime, fmt: str = "%Y-%m-%d") -> str:
    """Format a date or datetime using ``fmt``."""
    return dt.strftime(fmt)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def read_json_file(path: str | Path) -> Any:
    """Load and parse a JSON file. Raises FileNotFoundError / json.JSONDecodeError on problems."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json_file(path: str | Path, data: Any, indent: int = 2) -> None:
    """Write data as formatted JSON to path, creating parent dirs if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, default=str)


# ---------------------------------------------------------------------------
# UUID helper (re-export for backward compatibility)
# ---------------------------------------------------------------------------

def new_uuid() -> str:
    """Generate a new UUID."""
    return str(uuid.uuid4())
