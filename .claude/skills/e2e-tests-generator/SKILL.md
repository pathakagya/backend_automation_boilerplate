# E2E Tests Generator Skill

## 1. Name + Trigger

**Skill Name**: `e2e-tests-generator`

**Trigger**: `/e2e-tests-generator --module-name <name> --feature <description>`

**Description**: A research-gated test writer. Its entire purpose is to stop Claude from
hallucinating table names, column names, endpoint paths, or enum values from training data or
plausible-sounding guesses. Every fact that ends up in a generated test must be traceable to a
verification step performed **this session** — never assumed.

## 2. Hard rule

**Never assume the following — always verify or ask:**
- Table/column names and their types
- Enum/status value sets (the exact strings the API/DB actually uses, not what sounds plausible)
- Endpoint paths and their request/response shapes
- Business rules that determine which scenarios are valid vs. invalid

If a fact can't be verified through the sources below, **stop and ask the user** rather than
generating a test built on a guess.

## 3. Phase sequence

### Phase 0 — Scope
Confirm module name, feature description, and tier (`smoke`/`integration`/`e2e`) with the user
if not already given.

### Phase 1 — Read local ground truth
Read: `src/core/constants.py` (existing table/column/endpoint constants), the module's existing
`conftest.py`/`test_*.py` if any, `tests/commons/data_builder/` for existing factories,
`tests/commons/api_schemas/` for existing response schemas. Build a private "reuse inventory" —
what already exists that this task should reuse rather than reinvent.

### Phase 2 — Enter plan mode
Before writing any code, switch to plan mode (or produce an explicit written plan if plan mode
isn't available in the current environment).

### Phase 3 — DB introspection
Verify table/column names and enum value sets against the **actual** database — via a connected
DB client/MCP tool if one is available, or by asking the user to confirm/paste a schema excerpt.
Never rely on memory or a plausible-sounding guess. For enum-like columns, get the actual
`DISTINCT` value set if possible rather than assuming it matches the field name's obvious values.

### Phase 4 — API contract verification
Verify endpoint paths, methods, and request/response shapes against real documentation (OpenAPI
spec, Postman collection, internal API docs), or by asking the user, or by finding an existing
call site in the codebase. Cross-check against `.env`/`.env.example` for the actual endpoint env
var names already in use.

### Phase 5 — Checklist / feature selection
List the concrete scenarios this task will cover (positive / negative / boundary /
acceptance-criteria) and confirm with the user before writing code if the scope is ambiguous.

### Phase 6 — Coverage gap analysis
Check what's *not* covered by the scenario list above — missing negative cases, missing DB-state
assertions, missing boundary values — and add them or explicitly note them as out of scope.

### Phase 7 — Plan with provenance
Present a plan table where every non-obvious fact carries a provenance tag, e.g.:
`DB: information_schema query` / `API docs: <link/file>` / `Existing code: <file:line>` /
`Confirmed with user`. Get explicit approval (exit plan mode) before implementing.

### Phase 8 — Implementation order
1. Constants (`src/core/constants.py`)
2. Schemas (`tests/commons/api_schemas/<module>_schemas.py`)
3. Factories (`tests/commons/data_builder/<module>.py`)
4. API client methods (`api/<module>_client.py`)
5. Fixtures (`conftest.py`)
6. Tests

Map SOLID/DRY onto this framework's own vocabulary while implementing: one test method per
scenario (SRP); tests call the typed client/DB helper, never raw `requests`/cursors (DIP).

### Phase 9 — Verify by running, not by asserting
Actually run `python -m py_compile <new files>` and `pytest tests/<tier>/<module>/ --collect-only`
and show the real output — do not report success without having run these.

## 4. Notes

- The specific introspection tools available (a DB MCP server, a docs MCP server, plain file
  reads) vary by environment — use whatever's connected; the phase sequence and the "never
  assume" rule are what matters, not any particular tool name.
- If DB/API access genuinely isn't available in the current environment, say so explicitly and
  ask the user for the missing facts rather than filling gaps with guesses.
