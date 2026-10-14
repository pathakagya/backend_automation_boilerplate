"""
StateManager: Tracks test state across multi-step test workflows.

Used when a test (or test suite) involves sequential steps where
values from step N are needed in step N+1.

Basic usage:
    def test_create_and_verify(api_session, state):
        # Step 1 – create resource
        resp = api_session.post("/orders", json={...})
        state.set("order_id", resp.json()["id"])

        # Step 2 – verify in DB
        order_id = state.get("order_id")
        row = db.fetch_one("SELECT * FROM orders WHERE id = :1", [order_id])
        assert row is not None

Extending for a specific domain:
    class OrderState(StateManager):
        @property
        def order_id(self) -> str:
            return self.require("order_id")

        @property
        def customer_id(self) -> str:
            return self.require("customer_id")
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


class StateKeyError(KeyError):
    """Raised when a required state key is missing."""


class StateManager:
    """
    Dictionary-backed state store for multi-step test workflows.

    Features:
        - Simple get / set / delete interface
        - require() raises a clear error when a key is absent
        - History: each set() records a timestamp
        - snapshot() for debugging / Allure attachment
        - clear() for test isolation
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._timestamps: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Core interface
    # ------------------------------------------------------------------ #

    def set(self, key: str, value: Any) -> None:
        """Store a value under key."""
        self._store[key] = value
        self._timestamps[key] = datetime.now(tz=timezone.utc).isoformat()

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for key, or default if absent."""
        return self._store.get(key, default)

    def require(self, key: str) -> Any:
        """
        Return the value for key.
        Raises StateKeyError if the key was never set.
        """
        if key not in self._store:
            available = list(self._store.keys())
            raise StateKeyError(
                f"State key {key!r} not found.\n"
                f"Available keys: {available}\n"
                f"Call state.set({key!r}, value) in an earlier test step."
            )
        return self._store[key]

    def delete(self, key: str) -> None:
        """Remove a key from state (no-op if absent)."""
        self._store.pop(key, None)
        self._timestamps.pop(key, None)

    def has(self, key: str) -> bool:
        """Return True if key exists in state."""
        return key in self._store

    def clear(self) -> None:
        """Remove all stored state. Called automatically by fixtures on teardown."""
        self._store.clear()
        self._timestamps.clear()

    # ------------------------------------------------------------------ #
    # Convenience: update many at once
    # ------------------------------------------------------------------ #

    def update(self, data: dict[str, Any]) -> None:
        """Batch-set multiple keys from a dict."""
        for key, value in data.items():
            self.set(key, value)

    # ------------------------------------------------------------------ #
    # Inspection / debugging
    # ------------------------------------------------------------------ #

    def snapshot(self) -> dict[str, Any]:
        """
        Return a dict copy of all stored values with their timestamps.
        Useful for attaching to Allure reports:

            import allure, json
            allure.attach(
                json.dumps(state.snapshot(), indent=2, default=str),
                name="Test State",
                attachment_type=allure.attachment_type.JSON,
            )
        """
        return {
            key: {"value": value, "set_at": self._timestamps.get(key)}
            for key, value in self._store.items()
        }

    def keys(self) -> list[str]:
        """Return the names of values currently stored for the test."""
        return list(self._store.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def __repr__(self) -> str:
        return f"StateManager(keys={list(self._store)})"
