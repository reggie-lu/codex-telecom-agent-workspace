# Execution Plan Protocol

## Purpose

ExecPlans are living documents for substantial implementation work. They prevent a long Codex
session from depending on chat memory.

## When an ExecPlan Is Required

Use one when work:

- Spans several meaningful files or modules.
- Creates a new subsystem.
- Changes architecture.
- Requires migration.
- Contains substantial uncertainty.
- Is difficult to review as one small patch.

Do not create an ExecPlan for trivial fixes.

## Plan Lifecycle

1. Inspect the repository.
2. Understand relevant `PRODUCT.md` and `ARCHITECTURE.md` requirements.
3. Create `.agent/plans/active/<feature>.md`.
4. Ask the human about unresolved product or architecture decisions.
5. Obtain approval for substantial scope or design.
6. Implement using TDD.
7. Keep Progress, Decisions, and Discoveries updated.
8. Verify.
9. Write Result.
10. Move the plan to `completed/`.

## ExecPlan Template

```markdown
# <Feature Name>

## Goal
Observable outcome.

## Requirement References
- UC-XXX
- FR-XXX

## Non-Goals
Explicit boundaries.

## Current State
What relevant code currently does.

## Proposed Design
Smallest design that satisfies approved requirements.

## Files Expected to Change
List expected files. This is a forecast, not permission for unnecessary changes.

## Test Strategy
List behavior to prove BEFORE implementation.

## Implementation Steps
- [ ] Add failing behavior test
- [ ] Implement minimum behavior
- [ ] Run targeted test
- [ ] Run relevant verification

## Open Questions
Questions requiring human input.

## Decisions
Important decisions discovered during implementation.

## Discoveries
Unexpected facts about the existing code or system.

## Progress
Keep accurate throughout work.

## Verification
Commands and expected outcomes. Only use commands configured by the project.

## Result
- Behavior delivered
- Tests added
- Deviations from the original plan
- Remaining risks or follow-ups
```
