from typing import Any

from tests.e2e.data_builders.shared import ProjectBaseFactory


class UserFactory(ProjectBaseFactory):
    """Standard user payload for POST /users."""

    @classmethod
    def create_payload(cls, **overrides: Any) -> dict[str, Any]:
        payload = {
            "username": f"user_{cls._generate_random_number(digits=6)}",
            "email":    cls._faker.email(),
            "role":     "member",
            "active":   True,
        }
        payload.update(overrides)
        return payload


class AdminUserFactory(ProjectBaseFactory):
    """User payload with admin role."""

    @classmethod
    def create_payload(cls, **overrides: Any) -> dict[str, Any]:
        payload = {
            "username": f"admin_{cls._generate_random_number(digits=6)}",
            "email":    cls._faker.email(),
            "role":     "admin",
            "active":   True,
        }
        payload.update(overrides)
        return payload
