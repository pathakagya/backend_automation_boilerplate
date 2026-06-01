"""
Project-level base factory.

All feature factories extend this class.
Provides _faker and _generate_random_number() shared across every factory in this project.

Usage:
    from tests.e2e.data_builders.shared import ProjectBaseFactory

    class ProductFactory(ProjectBaseFactory):
        @classmethod
        def create_payload(cls, **overrides):
            payload = {
                "name": f"product_{cls._generate_random_number(digits=4)}",
                "price": cls._faker.pyfloat(min_value=1, max_value=999, right_digits=2),
            }
            payload.update(overrides)
            return payload
"""
from helpers.data_builders import BaseFactory


class ProjectBaseFactory(BaseFactory):
    """Extend this (not BaseFactory directly) for all project feature factories."""
