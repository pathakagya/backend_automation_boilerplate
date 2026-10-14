# Requirements-to-tests skill

## Purpose

Turn an approved Jira issue or specification into a provenance-backed test
design and then hand it to the existing generation skills.

## Required input

1. If Jira MCP is connected, ask for the Jira issue key and read the issue,
   acceptance criteria, comments, linked issues, and attachments.
2. If Jira is unavailable or no key is supplied, require a specification and
   explicit acceptance criteria from the user.
3. Ask for the module, environment, API services, and whether DB validation is
   in scope.

Do not generate tests from a vague feature description.

## Research gate

Verify endpoint paths, methods, payloads, response shapes, error behavior,
authentication roles, database objects, columns, relationships, enum values,
and asynchronous side effects from authoritative evidence. Use the connected
Jira/DB tools, OpenAPI/Postman/backend source, project registries, or explicit
user confirmation.

Record the source beside every non-obvious fact in
`docs/TEST_DESIGN_TEMPLATE.md`. If a fact cannot be verified, stop and ask;
never infer it.

## Design gate

Produce:

1. acceptance-criteria mapping;
2. smoke, integration, and e2e scenario matrix;
3. positive, negative, boundary, authorization, persistence, and side-effect
   coverage;
4. data setup and cleanup plan;
5. explicit coverage gaps;
6. implementation order and expected evidence.

Pause for QA engineer approval. The QA lead owns the approval process. Backend
review is valuable but optional when unavailable.

## Implementation handoff

After approval, invoke the appropriate existing skills in this order:

1. `setup-test-module`;
2. `generate-api-client`;
3. `generate-conftest`;
4. `generate-data-builder` when writes/prerequisites require it;
5. `generate-test-file`;
6. `e2e-tests-generator` for research-gated workflow tests;
7. design and quality review agents.

Generated and modified methods must include accurate documentation following
`docs/METHOD_DOCUMENTATION.md`. Link project methods to their verified evidence
where the method encodes endpoint or DB behavior.

## Verification

Run collection and the relevant test tier. Report real output. Confirm that
Allure/JUnit evidence is sanitized and that the Jira/spec identifier is present
in test metadata when configured.

