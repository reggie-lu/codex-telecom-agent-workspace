# Project Working Agreement

## Mission

This repository is developed collaboratively between the human and Codex. The human owns product
direction, scope, and important architecture decisions. Codex organizes requirements, proposes
options, implements approved work, writes tests, verifies behavior, and keeps documentation aligned.

## Source of Truth

1. `docs/PRODUCT.md` — WHAT and WHY
2. `docs/ARCHITECTURE.md` — WHERE and HOW
3. `docs/DECISIONS.md` — approved decisions and rationale
4. `docs/FEATURE_HISTORY.md` — human-verified development checkpoints
5. `.agent/plans/active/*.md` — current work
6. `tests/` — executable behavioral contracts
7. Source code

Surface conflicts; never silently choose one source over another.

## Human-in-the-Loop Rule

Ask one focused question before filling missing product or architecture information. Provide options
when useful, wait for the answer, organize it, and confirm major decisions. Never turn an example
into a requirement unless the human selects it.

## Scope Discipline

- Make the smallest coherent change.
- Do not implement unrelated improvements or hypothetical abstractions.
- Propose extra work instead of silently doing it.
- Avoid dependencies unless justified by approved requirements.

## TDD Rule

For behavioral changes: define expected behavior, add a failing test, implement the minimum change,
run the targeted test, refactor only if useful, then run relevant verification.

## Planning and Verification

Use `.agent/PLANS.md` for substantial work. Before completion, run approved verification commands;
if one cannot run, report why and what uncertainty remains.

## Documentation Rule

Store durable product and architecture information in `PRODUCT.md`, `ARCHITECTURE.md`, and
`DECISIONS.md`. Store temporary implementation context in active ExecPlans. Avoid duplication.

## Run and Verification Documentation

Every implemented slice must document how a human can run and verify it, even when the procedure is
temporary and expected to change later. Keep copy-pasteable setup, run, verification, expected
result, and cleanup commands in `README.md` or a linked runbook. Update or replace stale commands as
the runtime evolves; do not leave the only working procedure in chat history or a completed
ExecPlan.

## Human-Verified Checkpoints

After Codex verification and explicit confirmation that the human has tested a feature successfully:

1. Update `docs/FEATURE_HISTORY.md` with local date and time, big-picture stage, feature breakdown,
   verification evidence, known limitations, branch, and implementation commit.
2. Clearly label the record as a development checkpoint rather than a production release.
3. Review the complete diff for secrets and unrelated files.
4. Commit with a concise feature-oriented message and push the current feature branch to its
   configured remote.
5. Report the branch, commit, push result, and any verification that was not run.

Do not claim human verification before the human confirms it. If commit or push fails, preserve the
local work and report the failure instead of claiming that the checkpoint is remote.

## Architecture Flow Maintenance

When the human and Codex agree to build a feature, update the architecture flow drawing in
`docs/ARCHITECTURE.md` in the same documentation or implementation slice. Show whether each node is
implemented, agreed but not implemented, or deferred. Update the drawing again whenever feature
boundaries, dependencies, or deployment stages change; do not add speculative components as if they
were approved.
