# Current-plan quality remediation

## Goal

Raise the unchanged 16-case live current-plan evaluation above the approved release gate by fixing
the two known deterministic intent misses and diagnosing the recurring-charge grounding rejection,
without weakening the safety gate.

## Requirement References

- `docs/PRODUCT.md`: grounded current-plan answers and safe failure behavior.
- `docs/ARCHITECTURE.md`: deterministic orchestration, MiniMax-M3 generation, grounding guard, and
  evaluation flow.
- `docs/DECISIONS.md`: approved 80% routine and 100% safety gates.
- Human-approved remediation after the 2026-08-26 live baseline: support the two missed
  paraphrases, diagnose the recurring-charge failure, and rerun the same evaluation.

## Non-Goals

- Adding billing, roaming, savings, or escalation behavior.
- Changing the 16-case dataset or lowering either evaluation threshold.
- Replacing the deterministic grounding guard with model-based grading.
- Changing the SambaNova model from `MiniMax-M3`.

## Current State

The live baseline passes 7/10 routine cases and 6/6 safety cases. The deterministic matcher misses
`routine-09-natural-data` and `routine-10-mobile-service`. `routine-05-recurring-charge` reaches the
model but its output is safely rejected by the grounding guard.

## Proposed Design

Add only the two approved intent phrases to the deterministic matcher. Inspect the raw synthetic
live output for the recurring-charge case, then make the smallest prompt or guard correction that
preserves all existing injection and unsupported-claim protections. Evaluate every change against
the same versioned dataset.

## Files Expected to Change

- `src/telecom_agent/services/send_current_plan_message.py`
- `src/telecom_agent/adapters/sambanova/current_plan_answers.py` if diagnosis identifies a prompt issue
- Unit and evaluation tests
- `README.md`, `evals/README.md`, and relevant durable docs
- `learning.md` and `blog.md`

## Test Strategy

First add failing unit expectations for both intent paraphrases and update the offline evaluator
expectation to 10/10. Preserve all grounding-guard tests. After implementation, run targeted tests,
the full test suite, Ruff, mypy, offline evaluation, and the unchanged live evaluation.

## Implementation Steps

1. Record the active plan and agreed intent stage in the architecture flow.
2. Add failing tests for the two intent paraphrases.
3. Implement the minimal matcher expansion and verify the offline gate.
4. Inspect the recurring-charge live output and adjust only the responsible layer.
5. Run all automated verification and update runbooks and project journals.
6. Ask the human to reproduce the live evaluation before any checkpoint commit or push.

## Open Questions

None. The remediation scope and unchanged evaluation gates are approved.

## Decisions

- Keep the dataset and thresholds unchanged so the result remains comparable to CP-005.
- Prefer a prompt correction over relaxing the grounding guard if the model output is merely
  duplicating an approved value.

## Discoveries

- The recurring-charge live output was only `Your monthly recurring charge is JPY 4,500.` It was
  accurate but omitted the other three values required by the grounded evidence contract.
- A prompt instruction to include all four canonical values exactly once fixed the live failure;
  no guard relaxation was necessary.

## Progress

- [x] Inspected the current matcher, grounding guard, evaluation cases, tests, and architecture flow.
- [x] Added failing behavioral tests.
- [x] Implemented and verified intent remediation.
- [x] Diagnosed and remediated recurring-charge behavior.
- [x] Updated documentation and journals.
- [x] Completed automated verification.
- [x] Received independent human verification.

## Verification

Focused tests pass. The unchanged offline and live evaluations both pass 10/10 routine and 6/6
safety. The full suite passes 65/65 with local PostgreSQL integration coverage. Ruff and mypy pass.
The human independently reran live mode and reproduced 10/10 routine, 6/6 safety, and a passing
release gate.

## Result

The unchanged evaluation dataset now passes both offline and live gates. The implementation adds
only two approved intent phrases and a stricter completeness instruction for MiniMax-M3. It does
not relax the grounding guard, thresholds, or adversarial cases. Human verification is complete;
this plan is ready for its development checkpoint.
