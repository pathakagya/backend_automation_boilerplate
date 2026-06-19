"""
StateManager extensions — typed state managers for domain-specific test workflows.

Provides patterns for creating project-specific state managers with type-safe property access.

Example:
    from core.state_extensions import TypedStateManager

    class OrderState(TypedStateManager):
        @property
        def order_id(self) -> str:
            return self.require_str("order_id")

        @property
        def customer_id(self) -> str:
            return self.require_str("customer_id")

        @property
        def total_amount(self) -> float:
            return self.require_float("total_amount")
"""
from __future__ import annotations

from typing import Any, TypeVar

from core.state_manager import StateManager, StateKeyError

T = TypeVar("T")


class TypedStateManager(StateManager):
    """
    Base class for creating typed state managers with domain-specific properties.

    Extends StateManager with type-safe getters that enforce value types.

    Usage:
        class UserState(TypedStateManager):
            @property
            def user_id(self) -> str:
                return self.require_str("user_id")

            @property
            def email(self) -> str:
                return self.require_str("email")

            @property
            def created_at(self) -> str:
                return self.require_str("created_at")
    """

    def require_str(self, key: str) -> str:
        """Require a string value."""
        value = self.require(key)
        if not isinstance(value, str):
            raise TypeError(
                f"State key {key!r} is {type(value).__name__}, expected str"
            )
        return value

    def require_int(self, key: str) -> int:
        """Require an integer value."""
        value = self.require(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(
                f"State key {key!r} is {type(value).__name__}, expected int"
            )
        return value

    def require_float(self, key: str) -> float:
        """Require a float value (or int, which can be cast to float)."""
        value = self.require(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(
                f"State key {key!r} is {type(value).__name__}, expected float or int"
            )
        return float(value)

    def require_bool(self, key: str) -> bool:
        """Require a boolean value."""
        value = self.require(key)
        if not isinstance(value, bool):
            raise TypeError(
                f"State key {key!r} is {type(value).__name__}, expected bool"
            )
        return value

    def require_dict(self, key: str) -> dict[str, Any]:
        """Require a dict value."""
        value = self.require(key)
        if not isinstance(value, dict):
            raise TypeError(
                f"State key {key!r} is {type(value).__name__}, expected dict"
            )
        return value

    def require_list(self, key: str) -> list[Any]:
        """Require a list value."""
        value = self.require(key)
        if not isinstance(value, list):
            raise TypeError(
                f"State key {key!r} is {type(value).__name__}, expected list"
            )
        return value

    def get_str(self, key: str, default: str = "") -> str:
        """Get a string value with default."""
        value = self.get(key, default)
        return value if isinstance(value, str) else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an int value with default."""
        value = self.get(key, default)
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float value with default."""
        value = self.get(key, default)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a bool value with default."""
        value = self.get(key, default)
        return value if isinstance(value, bool) else default

    def get_dict(self, key: str, default: dict | None = None) -> dict[str, Any]:
        """Get a dict value with default."""
        if default is None:
            default = {}
        value = self.get(key, default)
        return value if isinstance(value, dict) else default

    def get_list(self, key: str, default: list | None = None) -> list[Any]:
        """Get a list value with default."""
        if default is None:
            default = []
        value = self.get(key, default)
        return value if isinstance(value, list) else default


class ContextualState(TypedStateManager):
    """
    State manager that tracks context/metadata about the test environment.

    Useful for multi-user or multi-tenant scenarios where tests run in parallel.

    Example:
        state = ContextualState()
        state.set_context("tenant_id", "acme-corp")
        state.set_context("user_id", "user-123")

        tenant = state.get_context("tenant_id")
        user = state.get_context("user_id")
    """

    def __init__(self) -> None:
        super().__init__()
        self._context: dict[str, Any] = {}

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value (not timestamped like regular state)."""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self._context.get(key, default)

    def has_context(self, key: str) -> bool:
        """Check if context key exists."""
        return key in self._context

    def clear_context(self) -> None:
        """Clear all context."""
        self._context.clear()

    def clear(self) -> None:
        """Clear all state and context."""
        super().clear()
        self._context.clear()

    def context_snapshot(self) -> dict[str, Any]:
        """Get current context snapshot."""
        return dict(self._context)
