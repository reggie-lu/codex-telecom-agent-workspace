# Cross-feature MVP evaluation baseline

## Goal

Add a versioned deterministic evaluation suite for latest-bill explanation, unexpected-charge
grounding, conversation-history integrity/privacy, and contextual escalation so the focused MVP has
repeatable routine-quality and release-blocking safety evidence beyond current-plan support.

## Requirement References

- `docs/PRODUCT.md`: 80% routine target, mandatory 100% missing/unavailable and
  conflicting/outdated safety, privacy, escalation reliability, and open evaluation work.
- `docs/ARCHITECTURE.md`: public service/API boundaries, customer isolation, typed evidence,
  immutable handoff context, and deterministic test adapters.
- `docs/DECISIONS.md`: split deterministic gates for current-plan evaluation and all accepted
  billing, history, and escalation contracts through D-035.
- Human approval on 2026-08-26 to implement the recommended cross-feature MVP evaluation slice.

## Non-Goals

- An LLM judge, live MiniMax-M3 calls, or changing the existing current-plan dataset.
- New product behavior, provider integrations, endpoints, or migrations.
- Plan comparison, roaming-option, or savings recommendation evaluation.
- Load, latency, production security, or real KDDI evaluation.

## Current State

The focused MVP paths now have a human-verified 36-case deterministic baseline. History and
escalation routine gates and all safety cases pass; latest-bill and unexpected-charge routine gates
are blocked by four preserved natural-language intent gaps.

## Proposed Design

Create versioned cross-feature cases and a deterministic offline runner that invokes real services
or API boundaries with evaluation-only fakes. Grade status, uncertainty, evidence, canonical facts,
message ordering, ownership privacy, escalation state, retry guidance, and prohibited claims.
Report feature-level routine scores and a global safety score, with a nonzero exit when any approved
gate fails. Keep the existing current-plan runner and historical baseline unchanged.

## Files Expected to Change

- Versioned evaluation datasets and documentation
- Cross-feature evaluation runner and deterministic scenarios
- Evaluation unit tests and regression assertions
- README, architecture, decisions, learning notes, blog, and this ExecPlan

## Test Strategy

Use tests-first cases for dataset validation, deterministic reproducibility, each grading
dimension, per-feature reporting, global safety blocking, and CLI exit behavior. Run the new suite,
all PostgreSQL tests, lint, strict typing, migration drift, and the unchanged current-plan gate.

## Implementation Steps

1. Approve gate granularity, baseline size, and case allocation.
2. Approve exact routine and safety scenarios before encoding them.
3. Add failing dataset/runner/grader tests.
4. Implement the smallest deterministic evaluation runner and versioned cases.
5. Record baseline results and update runbooks and architecture.
6. Complete automated checks and request independent human verification.

## Open Questions

None.

## Decisions

- Remain deterministic and offline; do not call MiniMax-M3 for these deterministic MVP paths.
- Preserve the existing current-plan dataset, thresholds, and historical comparability.
- Keep routine and mandatory safety results separate; no routine score can offset a safety failure.
- Require each of latest bill, unexpected charge, conversation history, and escalation to score at
  least 80% on its own routine cases. Require 100% across the combined safety set; any failed gate
  blocks the overall release gate.
- Use a balanced 36-case baseline: five routine and four safety cases for each of the four features,
  totaling 20 routine and 16 mandatory safety cases.
- Use the approved scenario catalog: bill requests for summary/invoice/period/total/items plus
  missing/empty/non-reconciling/negative data; charge requests for higher/unexpected/roaming/
  JPY 1,200/unrecognized usage plus missing/stale/conflicting/ambiguous evidence; history cases for
  empty/plan/bill/charge/mixed histories plus authentication/not-found/cross-customer/disclosure;
  escalation cases for queued/trimmed/status/context/empty requests plus invalid/duplicate/
  cross-customer/provider-failure behavior.
- Provide one aggregate offline command, `uv run python -m telecom_agent.evaluation.mvp`, which
  always runs all 36 cases, prints every result, four feature routine scores, the combined safety
  score, and the overall gate, and exits nonzero on any gate failure. Do not add filters or live mode.

## Discoveries

- Existing implementation tests contain most required scenario fixtures, but evaluation cases must
  express product outcomes rather than mirror internal test functions.

## Progress

- [x] Selected and approved cross-feature MVP evaluation after CP-010.
- [x] Recorded the agreed evaluation architecture boundary.
- [x] Approved gate, dataset, and command contracts.
- [x] Added failing evaluation tests.
- [x] Implemented the versioned runner and cases.
- [x] Updated run and verification documentation.
- [x] Completed automated and human verification.

## Verification

The full PostgreSQL-enabled suite passes 114/114; Ruff and strict mypy pass across 74 source files.
The unchanged current-plan gate passes 10/10 routine and 6/6 safety. The first cross-feature command
run produced bill 3/5, charge 3/5, history 5/5, escalation 5/5, safety 16/16, and the expected failed
release gate. The human independently ran the documented command and reproduced every case result
and the same aggregate scores on 2026-08-26.

## Result

Completed and independently human-verified on 2026-08-26. The evaluator is ready to measure a
separate quality-remediation slice without changing its dataset, thresholds, or safety contract.
