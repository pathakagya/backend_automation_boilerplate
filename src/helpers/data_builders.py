"""
Data builder helpers — factory pattern for building test data dicts.

Usage:
    from helpers.data_builders import BaseFactory

    class UserFactory(BaseFactory):
        @classmethod
        def create_payload(cls, **overrides):
            payload = {
                "username": f"user_{cls._generate_random_number(digits=6)}",
                "email":    cls._faker.email(),
                "role":     "member",
            }
            payload.update(overrides)
            return payload

    # Single payload
    user = UserFactory.create_payload()

    # With overrides
    user = UserFactory.create_payload(role="admin")

    # Multiple payloads
    users = UserFactory.create_many(3, role="member")
"""
from __future__ import annotations

from typing import Any

from faker import Faker
from helpers.common import random_string, random_int, random_email, unique_id


class BaseFactory:
    _faker = Faker()

    @classmethod
    def _generate_random_number(cls, digits: int = 3) -> str:
        return str(cls._faker.random_number(digits=digits, fix_len=True))

    @classmethod
    def create_payload(cls) -> dict[str, Any]:
        raise NotImplementedError("Subclasses must implement create_payload()")

    @classmethod
    def create_many(cls, count: int, **overrides: Any) -> list[dict[str, Any]]:
        """Call create_payload() count times; each gets its own random values."""
        return [cls.create_payload(**overrides) for _ in range(count)]
