# Boilerplate boundaries

This repository contains two things:

1. A reusable backend test framework that can be forked by any company project.
2. A working Vyaguta reference implementation used to prove the framework against
   real API and database behavior.

The Vyaguta reference is valuable context, but its endpoints, tables, schemas,
roles, credentials, and business rules are not generic defaults. A new project
must verify its own facts from an API contract, database inspection, or approved
specification.

## Layer ownership

| Layer | Shared responsibility | Project responsibility |
|---|---|---|
| `src/core/` | Configuration, HTTP lifecycle, state, generic DB contract | No vendor drivers or domain facts |
| `src/helpers/` | Generic assertions, polling, payload and query helpers | No project business rules |
| `api/` | Typed client base and client conventions | Endpoint methods and service-specific auth |
| `tests/commons/` | Assertion/schema/factory extension points | Domain schemas, factories, registries |
| `tests/smoke/` | Health and sample-contract patterns | Project endpoints and critical-path checks |
| `tests/integration/` | API/DB comparison patterns | Tables, views, joins, and expected mappings |
| `tests/e2e/` | Workflow conventions | Business scenarios, seed plans, cleanup |
| `src/project/db/` | Reference adapter location | Vendor driver, connection, metadata, seeders |

## Vyaguta reference

The current Users implementation and `Core.postman_collection.json` are retained
as a worked example. Read them to understand structure and evidence collection;
do not copy their endpoint paths or database names into another project without
verification.

Reference test examples are available at:

- `tests/smoke/vyaguta/test_users_reference_smoke.py`
- `tests/integration/vyaguta/test_users_count.py`
- `tests/e2e/users/test_user_workflow_example.py`
- `tests/e2e/users/test_create_user.py` for comprehensive positive, negative,
  boundary, and API/DB field-mapping coverage.

The reference constants are grouped in `core.constants.VyagutaReference` and the
domain constants remain visibly separate from generic smoke defaults.

## First fork checklist

1. Replace the project identity and environment documentation.
2. Configure `API_BASE_URL` and the selected authentication mechanism.
3. Add a project-owned DB adapter only if DB-backed tests are required.
4. Register project endpoint, schema, table, and relationship facts.
5. Add one API sample-contract test and one smoke health test.
6. Run API-only smoke first:

   ```bash
   pytest -m "smoke and not db_required" -ra
   ```

7. Run DB-backed tiers only after the adapter health check passes.

