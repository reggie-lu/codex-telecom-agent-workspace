# Current-Plan Evaluation Baseline

## Goal

Create a reproducible 16-case evaluation baseline for the grounded current-plan flow, with a
routine-quality gate of at least 80%, a release-blocking safety gate of 100%, deterministic ordinary
execution, and an explicit opt-in live `MiniMax-M3` mode.

## Requirement References

- Section 9 of `docs/PRODUCT.md`
- D-010, D-015, D-017, D-022, and D-023
- `docs/ARCHITECTURE.md` section 10
- Human approval of 10 routine plus 6 safety/adversarial cases on 2026-08-26

## Non-Goals

- Billing, charge, roaming, savings, comparison, history, or escalation evaluations.
- An LLM-as-judge or OpenAI-hosted evaluation dependency.
- Semantic grading beyond explicit current-plan contract checks.
- CI/CD, dashboards, historical result storage, or production release automation.
- Broad intent-classifier redesign, production prompt changes, API changes, database migrations, or
  model changes. Small defects directly exposed by the approved baseline may be fixed test-first.

## Current State

The current-plan service has unit, API, adapter, and PostgreSQL tests plus two successful manual
live requests. There is no versioned representative dataset, aggregate scoring, release-gate
calculation, or one-command live evaluation.

## Proposed Design

- Store 16 versioned JSONL cases under `evals/cases`: 10 routine and 6 safety.
- Each case declares input, fixture state, deterministic generator behavior, expected status,
  uncertainty, evidence count, required terms, prohibited terms, and whether live generation applies.
- Run cases through the real framework-independent current-plan service using evaluation-only fakes
  for ownership, plan retrieval, and persistence.
- Grade each result with deterministic contract checks and emit per-case failures plus aggregate
  routine and safety scores.
- Permit release only when routine is at least 80% and safety is exactly 100%.
- In offline mode, use deterministic generator behaviors for every case. In live mode, use the
  configured SambaNova generator only for live-eligible supported cases; preserve deterministic
  missing-data, unsupported, and output-fault cases.
- Expose `uv run python -m evals.current_plan --mode offline|live` with no database dependency.

## Files Expected to Change

- `evals/__init__.py`
- `evals/current_plan.py`
- `evals/cases/current_plan.jsonl`
- `evals/README.md`
- `tests/evaluation/test_current_plan_evaluation.py`
- `README.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md`
- `learning.md` and `blog.md`

## Test Strategy

- Dataset contract: exactly 16 unique cases, 10 routine and 6 safety.
- Grading: correct output passes; each status, uncertainty, evidence, required-term, and prohibited-
  term mismatch is visible.
- Gates: routine 80% passes, below 80% fails, and any safety failure blocks release.
- Runner: the versioned offline suite is reproducible and reaches the approved gates.
- Live routing: only eligible supported cases use the supplied live generator.
- CLI: stable summary and nonzero exit when a gate fails or live configuration is missing.
- Full: pytest with PostgreSQL, Ruff, and strict mypy including `evals`.

## Implementation Steps

- [x] Confirm dataset size, groups, thresholds, and offline/live separation.
- [x] Review official evaluation/grader structure guidance.
- [x] Create the ExecPlan and update the agreed architecture flow.
- [x] Add the versioned dataset and failing evaluation tests.
- [x] Implement deterministic grading, gates, runners, and CLI output.
- [x] Run the offline baseline and document known failures.
- [x] Run one opt-in live baseline without exposing credentials.
- [x] Update durable decisions, runbooks, learning notes, and blog notes.
- [x] Run full automated verification.
- [x] Await human testing before checkpoint commit and push.

## Open Questions

None for this focused baseline. Historical result storage and semantic graders remain deferred.

## Decisions

- The initial evaluator is local and provider-neutral rather than hosted by OpenAI.
- Deterministic checks are authoritative for the current explicit contract.
- Live mode is opt-in, may incur provider usage, and cannot weaken deterministic safety gates.
- Aggregate routine and safety scores remain separate; they are never averaged together.

## Discoveries

- Official OpenAI documentation distinguishes string, Python, model, similarity, and combined
  graders. This baseline uses the equivalent of deterministic string/Python checks because its
  contract is explicit and account-specific safety should not depend on another model.
- The existing evaluation directory contains no executable assets.
- The first offline run scored routine 60% and safety 66.7% because terminal punctuation prevented
  otherwise supported `plan` questions from reaching the plan path. The natural cases remain in the
  dataset; a narrow punctuation-normalization fix is required rather than weakening their rubric.
- After the focused punctuation fix, offline scoring reached the approved 8/10 routine and 6/6
  safety gates. The two remaining routine failures document broader paraphrase gaps.
- The first live run scored 7/10 routine and 6/6 safety. `routine-05-recurring-charge` was safely
  rejected by the output guard in addition to the two known intent misses, so the live release gate
  failed without a safety violation.

## Progress

Implementation, Codex verification, and the required human live run are complete. The plan is
archived for the CP-005 development checkpoint; the failed live routine gate remains an explicit
next-work item rather than being reclassified as a pass.

## Verification

Completed on 2026-08-26:

```bash
.venv/bin/python -m telecom_agent.evaluation.current_plan --mode offline
.venv/bin/python -m telecom_agent.evaluation.current_plan --mode live
.venv/bin/ruff check .
.venv/bin/mypy src tests
TEST_DATABASE_URL=postgresql+psycopg://bowenl@127.0.0.1:55432/telecom_agent_test .venv/bin/pytest
```

- Offline baseline: routine 8/10 (80%, pass), safety 6/6 (100%, pass), release gate pass.
- Live baseline: routine 7/10 (70%, fail), safety 6/6 (100%, pass), release gate fail.
- Full pytest: 63 passed with isolated PostgreSQL.
- Ruff: passed.
- Strict mypy: passed across 51 source files.
- No database or real customer data was used by either evaluation mode.

## Result

Implemented the versioned 16-case dataset, deterministic contract graders, split release gates,
offline and live runner, actionable per-case output, configuration-safe CLI, a punctuation
regression fix discovered by the baseline, and complete run documentation. Human verification on
2026-08-26 reproduced the live 7/10 routine failure, 6/6 safety pass, and blocked release gate.
