# Backend test design template

Use this document before writing smoke, integration, or e2e tests.

## Intake

- Source: Jira key or specification path
- Feature/module:
- Environment:
- API services:
- Database adapter/capabilities:
- QA owner:
- QA approval:
- Backend reviewer (optional):

## Acceptance criteria

Copy each criterion verbatim and give it an ID:

```text
AC-001:
AC-002:
```

## Verified evidence

Every implementation fact needs a source.

| Fact | Value | Source/provenance | Verified date |
|---|---|---|---|
| HTTP method/path | | OpenAPI/Postman/backend code/user confirmation | |
| Request shape | | | |
| Response shape | | | |
| Status/error behavior | | | |
| DB table/view/columns | | Schema inspection/project registry | |
| Enum/status values | | Distinct DB/API values | |
| Relationships/side effects | | Schema/API behavior | |

Unknown facts are blockers. Do not replace them with plausible guesses.

## Scenario matrix

| ID | AC | Tier | Scenario | Expected API result | Expected DB/side effect | Evidence |
|---|---|---|---|---|---|---|
| SC-001 | AC-001 | smoke/integration/e2e | | | | |

Include, where applicable:

- happy path and alternate valid paths;
- required-field, invalid-type, invalid-enum, boundary, and duplicate cases;
- authentication, authorization, and role differences;
- API response schema and response-time expectations;
- persistence, relationships, soft-delete/history, and event-driven effects;
- cleanup and isolation requirements.

## Coverage gaps

List unverified or deliberately excluded scenarios:

```text
- GAP-001:
```

## Approval gate

Implementation may begin only after the QA engineer approves this matrix. The
QA lead owns the approval process. Backend review is requested when available,
but it is not a hard dependency when the QA lead accepts the evidence.

