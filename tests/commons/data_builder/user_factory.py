from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from tests.commons.data_builder.shared import ProjectBaseFactory

_OPTIONAL_FIELDS = (
    "middleName", "recruiteeUrl", "leaveIssuerId", "cvUrl", "roleIds",
    "pastExperience", "bloodGroup", "homePhone", "githubId", "coAppraiserId",
)


class UserFactory(ProjectBaseFactory):
    """
    Payload builder for POST /core/users.
    """

    @classmethod
    def create_payload(
        cls,
        *,
        department_id: int,
        designation_id: int,
        designation_name: str,
        area_id: int,
        area_name: str,
        engagement_status_id: int,
        team_manager_id: int,
        appraiser_id: int,
        engagement_status_name: str = "Probation",
        leave_issuer_id: Optional[int] = None,
        co_appraiser_id: Optional[int] = None,
        role_ids: Optional[list[int]] = None,
        **overrides: Any,
    ) -> dict[str, Any]:
      
        transition_date = date.today() - timedelta(days=365)  # join_date == transition_date, like the real collection
        mid_probation_date = transition_date + timedelta(days=90)
        end_probation_date = transition_date + timedelta(days=180)

        payload: dict[str, Any] = {
            "firstName": cls._faker.first_name(),
            "middleName": None,
            "lastName": cls._faker.last_name(),
            "joinDate": transition_date.isoformat(),
            "recruiteeUrl": "",
            "username": cls._unique_username(),
            "departmentId": department_id,
            "leaveIssuerId": leave_issuer_id,
            "teamManagerId": team_manager_id,
            "scheduledType": "FULL_TIME",
            "workingShift": "DAY_SHIFT",
            "availabilityTime": {
                "startTime": "09:00",
                "startTimeType": "AM",
                "endTime": "06:00",
                "endTimeType": "PM",
            },
            "roleIds": role_ids if role_ids is not None else [],
            "pastExperience": 0,
            "cvUrl": None,
            "gender": "FEMALE",
            "dateofBirth": "1990-01-01",
            "bloodGroup": "B-",
            "maritialStatus": "Single",
            "personalEmail": cls._faker.email(),
            "mobilePhone": cls._faker.numerify("98########"),
            "homePhone": None,
            "emergencyPhone": cls._faker.numerify("98########"),
            "emergencyContactRelationship": "mother",
            "temporaryAddress": cls._faker.city(),
            "permanentAddress": cls._faker.city(),
            "country": "Nepal",
            "timezone": "+05:45",
            "githubId": None,
            "designationAreaHistory": [
                {
                    "transitionDate": transition_date.isoformat(),
                    "designation": {"id": designation_id, "name": designation_name},
                    "area": {"id": area_id, "name": area_name},
                }
            ],
            "empStatusHistory": [
                {
                    "transitionDate": transition_date.isoformat(),
                    "engagementStatus": {"id": engagement_status_id, "name": engagement_status_name},
                    "empStatusDetails": [
                        {"category": "Mid Probation", "date": mid_probation_date.isoformat()},
                        {"category": "End Probation", "date": end_probation_date.isoformat()},
                    ],
                }
            ],
            "appraiserId": appraiser_id,
            "coAppraiserId": co_appraiser_id,
        }
        payload.update(overrides)
        return payload

    @classmethod
    def create_minimal_payload(cls, **kwargs: Any) -> dict[str, Any]:
        """Drop every field confirmed optional (see _OPTIONAL_FIELDS) to exercise that equivalence class."""
        payload = cls.create_payload(**kwargs)
        for field in _OPTIONAL_FIELDS:
            payload.pop(field, None)
        return payload

    @classmethod
    def _unique_username(cls) -> str:
        return f"{cls._generate_random_number(digits=8)}.{cls._faker.user_name()}@test.example.com"
