"""
Polling and wait helpers — synchronize on async operations and state changes.

Provides utilities for waiting until conditions are met, useful in:
- Waiting for API state changes to propagate
- Database eventual consistency checks
- Async operation completion verification
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


class PollingTimeoutError(TimeoutError):
    """Raised when polling condition is not met within timeout."""

    pass


def wait_until(
    condition: Callable[[], bool],
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.5,
    description: str = "condition",
) -> None:
    """
    Poll until a condition is true or timeout is reached.

    Args:
        condition: Callable that returns True when condition is met.
        timeout_seconds: Max time to wait (default 30s).
        poll_interval_seconds: Time between polls (default 0.5s).
        description: Description of what we're waiting for (for error messages).

    Raises:
        PollingTimeoutError: If condition not met within timeout.

    Example:
        wait_until(
            lambda: response.status_code == 200,
            timeout_seconds=10,
            description="API response to be successful"
        )
    """
    start_time = time.time()
    last_error = None

    while True:
        elapsed = time.time() - start_time

        try:
            if condition():
                return
        except Exception as e:
            last_error = e

        if elapsed >= timeout_seconds:
            error_msg = f"Timed out waiting for {description} (waited {elapsed:.2f}s)"
            if last_error:
                error_msg += f"\nLast error: {last_error}"
            raise PollingTimeoutError(error_msg)

        time.sleep(poll_interval_seconds)


def wait_for_value(
    func: Callable[[], T],
    expected: T,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.5,
    description: str = "value",
) -> T:
    """
    Poll until a function returns an expected value.

    Args:
        func: Callable that returns a value to compare.
        expected: Expected value (compared with ==).
        timeout_seconds: Max time to wait (default 30s).
        poll_interval_seconds: Time between polls (default 0.5s).
        description: Description for error messages.

    Returns:
        The value returned by func when it matches expected.

    Raises:
        PollingTimeoutError: If expected value not returned within timeout.

    Example:
        status = wait_for_value(
            lambda: db.fetch_one(...).status,
            "completed",
            timeout_seconds=60,
            description="order status to be 'completed'"
        )
    """
    start_time = time.time()
    last_value = None

    while True:
        elapsed = time.time() - start_time

        try:
            last_value = func()
            if last_value == expected:
                return last_value
        except Exception as e:
            pass

        if elapsed >= timeout_seconds:
            raise PollingTimeoutError(
                f"Timed out waiting for {description} "
                f"(waited {elapsed:.2f}s, last value: {last_value!r})"
            )

        time.sleep(poll_interval_seconds)


def wait_for_no_error(
    func: Callable[[], Any],
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.5,
    description: str = "operation",
) -> Any:
    """
    Poll until a function executes without raising an exception.

    Useful for eventual consistency checks where operations may initially fail.

    Args:
        func: Callable to execute repeatedly.
        timeout_seconds: Max time to wait (default 30s).
        poll_interval_seconds: Time between polls (default 0.5s).
        description: Description for error messages.

    Returns:
        The result of func when it succeeds.

    Raises:
        PollingTimeoutError: If func keeps raising exceptions after timeout.

    Example:
        user = wait_for_no_error(
            lambda: db.fetch_one("SELECT * FROM users WHERE id = %s", [user_id]),
            timeout_seconds=10,
            description="user to appear in database"
        )
    """
    start_time = time.time()
    last_error = None

    while True:
        elapsed = time.time() - start_time

        try:
            return func()
        except Exception as e:
            last_error = e

        if elapsed >= timeout_seconds:
            raise PollingTimeoutError(
                f"Timed out waiting for {description} "
                f"(waited {elapsed:.2f}s)\nLast error: {last_error}"
            )

        time.sleep(poll_interval_seconds)


def retry(
    func: Callable[[], T],
    max_attempts: int = 3,
    backoff_multiplier: float = 1.0,
    initial_delay_seconds: float = 1.0,
) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: Callable to retry.
        max_attempts: Maximum number of attempts (default 3).
        backoff_multiplier: Multiplier for exponential backoff (default 1.0 = no backoff).
        initial_delay_seconds: Initial delay between retries (default 1.0s).

    Returns:
        Result of func on successful execution.

    Raises:
        The last exception if all attempts fail.

    Example:
        response = retry(
            lambda: api_session.post("/orders", json={...}),
            max_attempts=5,
            backoff_multiplier=2.0,
            initial_delay_seconds=0.5
        )
    """
    last_error = None
    delay = initial_delay_seconds

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            last_error = e

            if attempt < max_attempts:
                time.sleep(delay)
                delay *= backoff_multiplier

    raise last_error


def poll_until_stable(
    func: Callable[[], T],
    stable_for_seconds: float = 2.0,
    timeout_seconds: float = 60.0,
    poll_interval_seconds: float = 0.5,
    description: str = "value",
) -> T:
    """
    Poll until a value stabilizes (remains unchanged for a period).

    Useful for checking if an eventually-consistent operation has completed.

    Args:
        func: Callable that returns a value.
        stable_for_seconds: How long value must remain unchanged (default 2.0s).
        timeout_seconds: Max time to wait (default 60s).
        poll_interval_seconds: Time between polls (default 0.5s).
        description: Description for error messages.

    Returns:
        The stable value.

    Raises:
        PollingTimeoutError: If value doesn't stabilize within timeout.

    Example:
        final_count = poll_until_stable(
            lambda: db.query("SELECT COUNT(*) as cnt FROM orders").cnt,
            stable_for_seconds=3.0,
            description="order count to stabilize"
        )
    """
    start_time = time.time()
    last_value = None
    stable_since = None

    while True:
        elapsed = time.time() - start_time

        try:
            current_value = func()

            if current_value == last_value:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since >= stable_for_seconds:
                    return current_value
            else:
                last_value = current_value
                stable_since = None

        except Exception:
            pass

        if elapsed >= timeout_seconds:
            raise PollingTimeoutError(
                f"Timed out waiting for {description} to stabilize "
                f"(waited {elapsed:.2f}s, last value: {last_value!r})"
            )

        time.sleep(poll_interval_seconds)
