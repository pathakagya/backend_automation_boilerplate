"""
General utilities used across tests and helpers.
"""
from __future__ import annotations

import json
import random
import string
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def random_string(length: int = 8, prefix: str = "") -> str:
    chars = string.ascii_lowercase + string.digits
    return prefix + "".join(random.choices(chars, k=length))


def random_int(min_val: int = 1, max_val: int = 9999) -> int:
    return random.randint(min_val, max_val)


def random_email(domain: str = "test.example.com") -> str:
    return f"{random_string(8)}@{domain}"


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def today_str(fmt: str = "%Y-%m-%d") -> str:
    return date.today().strftime(fmt)


def now_utc_str(fmt: str = "%Y-%m-%dT%H:%M:%SZ") -> str:
    return datetime.now(tz=timezone.utc).strftime(fmt)


def format_date(dt: date | datetime, fmt: str = "%Y-%m-%d") -> str:
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
# UUID helper
# ---------------------------------------------------------------------------

def new_uuid() -> str:
    return str(uuid.uuid4())
