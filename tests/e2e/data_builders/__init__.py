"""
Feature-wise data factories for E2E tests.

Structure:
    shared.py               ← ProjectBaseFactory (extend this for all factories)
    user_factory.py         ← UserFactory, AdminUserFactory
    order_factory.py        ← OrderFactory, BulkOrderFactory
    <feature>_factory.py    ← add one file per feature

Usage:
    from tests.e2e.data_builders.user_factory import UserFactory

    payload  = UserFactory.create_payload()
    payload  = UserFactory.create_payload(role="admin")
    payloads = UserFactory.create_many(3)
"""
