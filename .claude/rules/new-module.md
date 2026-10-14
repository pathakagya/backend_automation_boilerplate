# Adding a New Feature Module — Checklist

Follow these steps in order when adding a new feature module (e.g. "orders", "payments") to the
framework. `.claude/skills/setup-test-module/SKILL.md` automates steps 1-4.

## 1. Create the API client

```
api/<module>_client.py
```

A class extending `BaseAPIClient` — one typed method per endpoint. See
`.claude/rules/api-standards.md`.

## 2. Create the module's test folder

```
tests/e2e/<module>/           # or tests/integration/<module>/ for count-parity-only modules
├── conftest.py                ← module fixtures (api client, any module-specific lookups)
└── test_<module>.py
```

## 3. Add data factories

```
tests/commons/data_builder/<module>.py
```

Extend `ProjectBaseFactory` (`tests/commons/data_builder/shared.py`). Add the new factory class
to `tests/commons/data_builder/__init__.py`'s re-exports.

## 4. Add constants

Add to `src/core/constants.py`: any new table/column names (`DBTable`), endpoint paths
(`APIPath`), and status/state values the module needs. Never hardcode these inline.

## 5. Add schema validation (if the module has a response shape worth locking down)

```
tests/commons/api_schemas/<module>_schemas.py
```

One function per response shape, returning a `dict[str, type | tuple[type, ...]]`. See
`.claude/rules/assertions.md`.

## 6. Wire fixtures in the module's `conftest.py`

- `<module>_api_client(api_session)` — returns the typed client from step 1.
- Any module-specific DB lookup/precondition fixtures the tests need.
- Reuse the global `state`, `db_connection`, `api_session` fixtures from `tests/conftest.py` —
  don't redefine them.

## 7. Verify

```bash
pytest tests/e2e/<module>/ -ra -s   # new module in isolation

# full suite — confirm no interference with other modules
pytest tests/smoke -m smoke -ra && pytest tests/integration -m integration -ra && pytest tests/e2e -m e2e -ra
```
