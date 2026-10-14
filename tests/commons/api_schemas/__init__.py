"""
API response schemas — one file per module, one function per response shape.

A schema is a plain `dict[str, type | tuple[type, ...]]`, consumed by
`tests.commons.assertions.assert_response_schema`. Example shape:

    # tests/commons/api_schemas/orders_schemas.py
    def get_order_response_schema() -> dict:
        return {
            "id": int,
            "status": str,
            "cancelled_at": (str, type(None)),   # nullable: present, may be None
        }

Only add a schema once the real response shape is confirmed (live call, OpenAPI spec, or
existing verified test) — see `.claude/skills/e2e-tests-generator/SKILL.md`'s "never assume"
rule. This package intentionally ships empty: the Users reference module's exact response
envelope shape is explicitly documented as unconfirmed
(`docs/USERS_MODULE_TEST_DESIGN.md`, "Exact response envelope shape is undocumented"), so no
schema is fabricated for it here.
"""
