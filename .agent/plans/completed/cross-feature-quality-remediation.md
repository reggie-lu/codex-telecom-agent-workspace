# Cross-feature intent quality remediation

## Goal

Raise latest-bill and unexpected-charge routine scores above their independent 80% gates by
recognizing the four human-verified natural-language gaps while preserving the versioned 36-case
dataset, all graders, thresholds, and perfect safety behavior.

## Requirement References

- CP-011 and the human-reproduced baseline: bill 3/5, charge 3/5, history 5/5, escalation 5/5,
  safety 16/16, release gate fail.
- `docs/PRODUCT.md`: at least 80% routine quality and 100% mandatory safety.
- D-036 through D-040: independent feature gates, fixed case allocation/catalog, singular command,
  and preserved baseline failures.
- Human approval on 2026-08-26 for the narrow four-pattern remediation.

## Non-Goals

- Changing evaluation cases, thresholds, expected evidence, or safety graders.
- Adding semantic classifiers, LLM intent routing, model calls, or dependencies.
- Changing answer wording, persistence, APIs, or supported charge categories.
- Adding deferred plan comparison, roaming recommendations, or savings advice.

## Current State

Latest-bill intent requires the literal word `bill`, so `recent invoice` and `billing period` are
unsupported. Charge diagnosis recognizes diagnostic bill language and numbered `charged` requests,
but not direct `roaming charge` or unrecognized roaming usage. These four misses block two routine
gates while every safety case passes.

## Proposed Design

Extend the existing normalized deterministic matchers with only the approved invoice/period and
roaming/unrecognized patterns. Preserve ambiguous `this charge` clarification precedence and every
grounding, evidence, missing-data, conflict, privacy, and escalation boundary.

## Files Expected to Change

- Focused intent matcher and unit regression tests
- Evaluation/runbook status and durable remediation notes
- Architecture flow status, learning notes, blog, and this ExecPlan

## Test Strategy

Use the four existing failing evaluation cases as immutable red tests and add focused matcher-level
behavior tests through the public message service. Require all 36 cross-feature cases, all 16
current-plan cases, the full PostgreSQL suite, Ruff, and strict mypy to pass.

## Implementation Steps

1. Record the approved narrow remediation and unchanged safety constraints.
2. Add focused failing unit cases for all four phrasings.
3. Extend only the deterministic intent predicates.
4. Run targeted and complete evaluation gates.
5. Update baseline documentation and request independent human verification.

## Open Questions

None.

## Decisions

- Recognize `invoice`, `billing period`/latest statement, direct `roaming charge`, and the
  combination of `roaming` with `recognize`.
- Do not weaken ambiguous-charge clarification or infer any new causal facts.
- Keep the CP-011 dataset and results as historical evidence.

## Discoveries

- All four failures occur before data retrieval; grounding and safety outputs already behave
  correctly once the intended route is selected.

## Progress

- [x] Approved remediation against the unchanged baseline.
- [x] Added focused regression tests.
- [x] Implemented narrow intent recognition.
- [x] Updated documentation.
- [x] Completed automated verification.
- [x] Completed independent human verification.

## Verification

- Focused public API regressions: 4 passed.
- Full pytest suite with local PostgreSQL: 118 passed.
- Ruff: passed.
- Strict mypy over `src` and `tests`: passed.
- Current-plan offline gate: routine 10/10, safety 6/6, release PASS.
- Cross-feature gate: all four routine groups 5/5, safety 16/16, release PASS.
- Independent human run on 2026-08-27: all four routine groups 5/5, safety 16/16, release PASS.

## Result

The unchanged evaluator is green after changing only deterministic intent recognition. Independent
human verification reproduced every passing case and the release gate on 2026-08-27.
