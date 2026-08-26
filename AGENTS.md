# Project Working Agreement

## Mission

This repository is developed collaboratively between the human and Codex. The human owns product
direction, scope, and important architecture decisions. Codex organizes requirements, proposes
options, implements approved work, writes tests, verifies behavior, and keeps project documentation
synchronized.

## Source of Truth

Use this hierarchy:

1. `docs/PRODUCT.md` — product truth: WHAT and WHY
2. `docs/ARCHITECTURE.md` — architecture truth: WHERE and HOW
3. `docs/DECISIONS.md` — important approved decisions and rationale
4. `.agent/plans/active/*.md` — current work
5. `tests/` — executable behavioral contracts
6. Source code

If sources conflict, surface the conflict. Do not silently choose one.

## Human-in-the-Loop Rule

Before filling missing product or architecture information:

- Ask one focused question.
- Provide options if useful.
- Wait for human input.
- Organize the answer.
- Confirm major decisions.

Never convert an example into a requirement unless the human explicitly selects it.

## Scope Discipline

- Make the smallest coherent change.
- Do not implement unrelated improvements.
- Do not build hypothetical future abstractions.
- Propose extra work instead of silently doing it.
- Avoid new dependencies unless justified.

## TDD Rule

For behavioral changes:

1. Identify expected behavior.
2. Write or update a test.
3. Run it and confirm the expected failure.
4. Implement the minimum reasonable change.
5. Run the targeted test.
6. Refactor if useful.
7. Run relevant or full tests.

## Planning Rule

Use `.agent/PLANS.md` for substantial work.

## Verification Rule

Before completion, run the project's approved verification commands. If a command cannot run,
report the command, reason, and remaining uncertainty.

## Documentation Rule

Store durable information in `PRODUCT.md`, `ARCHITECTURE.md`, and `DECISIONS.md`. Store temporary
implementation context in active ExecPlans. Do not duplicate the same information everywhere.
