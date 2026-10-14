"""
Feature-wise data factories, one file per feature.

Structure:
    shared.py               ← ProjectBaseFactory (extend this for all factories)
    user_factory.py         ← UserFactory (POST /core/users payload builder)
    <feature>.py            ← add one file per feature

Every factory is re-exported here so callers don't need to know which file it lives in:

    from tests.commons.data_builder import UserFactory

    # FK ids (department/designation/area/engagement status, plus an existing user id for
    # teamManagerId/appraiserId — both required by the live API) come from a live DB lookup —
    # see the `lookup_data` fixture in tests/e2e/users/conftest.py.
    payload  = UserFactory.create_payload(department_id=1, designation_id=2, designation_name="...",
                                           area_id=1, area_name="...", engagement_status_id=4,
                                           team_manager_id=99, appraiser_id=99)
    payload  = UserFactory.create_minimal_payload(department_id=1, designation_id=2, designation_name="...",
                                                   area_id=1, area_name="...", engagement_status_id=4,
                                                   team_manager_id=99, appraiser_id=99)
    payloads = UserFactory.create_many(3, department_id=1, ..., team_manager_id=99, appraiser_id=99)
"""
from tests.commons.data_builder.shared import ProjectBaseFactory
from tests.commons.data_builder.user_factory import UserFactory

__all__ = ["ProjectBaseFactory", "UserFactory"]
