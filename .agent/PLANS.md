# Execution Plan Protocol

Use an ExecPlan for work spanning meaningful modules, creating a subsystem, changing architecture,
requiring migration, or containing substantial uncertainty. Do not create one for trivial fixes.

## Lifecycle

1. Inspect the repository and approved requirements.
2. Create `.agent/plans/active/<feature>.md`.
3. Ask about unresolved product or architecture decisions and obtain approval.
4. Implement with tests first and keep progress, decisions, and discoveries current.
5. Verify, record the result, and move the plan to `completed/`.

## Required Sections

Goal; Requirement References; Non-Goals; Current State; Proposed Design; Files Expected to Change;
Test Strategy; Implementation Steps; Open Questions; Decisions; Discoveries; Progress; Verification;
Result.
