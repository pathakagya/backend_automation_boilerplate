# Architecture

## Goals
- Reuse one boilerplate across multiple projects
- Keep core generic and driver-agnostic
- Make setup and extension explicit for humans and AI tools

## Layers
1. Configuration
- `ConfigManager` supports INI, YAML, ENV sources.
- Env vars override file values, enabling secure CI usage.

2. Core runtime
- `APISession` wraps `requests.Session` with auth, retries, timeout, and base URL.
- `DatabaseConnection` defines abstract DB lifecycle and query methods.
- `StateManager` stores workflow state per test function.

3. Fixtures
- `src/conftest.py` provides session-wide config.
- `src/fixtures/*` provides reusable fixture factories and defaults.
- `tests/conftest.py` is the project customization boundary.

4. Helpers
- Assertions and parsers for readable tests.
- API/DB helpers for common operations.
- Data builders for maintainable test payloads.

## Test strategy
- `smoke`: fast health checks
- `integration`: service or DB connectivity
- `e2e`: full workflow assertions

## Design decisions
- No DB driver imports in core modules.
- Config methods return plain dictionaries.
- Teardown is explicit using fixture `yield` patterns.
- Workflow state is local to each test via function-scoped `state`.

## How to adapt for a project
1. Add your DB subclass in project code.
2. Override `db_connection` fixture in `tests/conftest.py`.
3. Update config templates for your endpoints/schemas.
4. Add feature-level fixtures and tests.
