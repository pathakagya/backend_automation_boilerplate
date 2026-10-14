"""
Shared, project-facing test modules: assertions, data builders, API schemas.

Generic HTTP/DB assertion primitives and the base data-factory class ship with the boilerplate
in `helpers.assertions` / `helpers.data_builders` (reusable across any fork, independent of any
one project's business domain). This package holds the composition layer built on top of them
for *this* project's tests — import assertions/factories from here, not from `helpers.*`
directly, so there's a single, consistent entry point (see `.claude/rules/assertions.md` /
`.claude/rules/testing.md`).
"""
