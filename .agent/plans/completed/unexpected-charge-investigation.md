# Unexpected-charge investigation

## Goal

Implement the first `UC-003` vertical slice: identify the approved international-roaming line item
on Synthetic Alice's latest bill, explain its cause only when typed supporting evidence is present,
communicate uncertainty when it is absent or inconsistent, and give a safe next step.

## Requirement References

- `docs/PRODUCT.md`: `UC-003`, the primary unexpected-charge flow, `FR-003`, and mandatory safety
  behavior for missing, conflicting, outdated, or unavailable data.
- `docs/ARCHITECTURE.md`: typed bill/charge evidence, synthetic KDDI adapter, conversation-centric
  API, customer ownership, PostgreSQL persistence, and contextual escalation boundary.
- `docs/DECISIONS.md`: synthetic data, ports and adapters, explicit persistent types, deterministic
  safety rules, and latest-bill-before-diagnosis sequencing.
- Human approval on 2026-08-26 to proceed from latest-bill summary to unexpected-charge
  investigation.

## Non-Goals

- Deciding a dispute, issuing a refund, adjusting a bill, or changing a plan.
- Implementing the human-escalation API; this slice may recommend that next step.
- General diagnosis for every possible billing item.
- Real KDDI account data, website scraping, or production policy claims.
- Live MiniMax-M3 wording or a charge-specific evaluation suite; those remain separate slices.

## Current State

The approved latest bill contains a JPY 1,200 `International roaming data` line item, but no typed
event currently establishes when, where, or why it was created. Diagnostic questions therefore
remain unsupported.

## Proposed Design

Add a narrow unexpected-charge evidence provider that resolves the roaming line item to a typed
supporting event. Extend deterministic message intent routing for direct unexpected/high-bill
questions. When bill, line item, and event agree, persist a grounded answer referencing both the
bill snapshot and a typed charge-evidence snapshot. If the intended charge is ambiguous, ask a
clarifying question without claiming a cause. If evidence is missing, stale, or conflicting, return
an uncertain limitation and recommend human support without inventing an explanation.

## Files Expected to Change

- Billing/charge domain types and message orchestration
- Synthetic KDDI and PostgreSQL adapters
- Message evidence persistence and a forward-only Alembic migration
- API, unit, contract, and integration tests
- README and durable project documentation
- `learning.md` and `blog.md`

## Test Strategy

Use TDD for grounded explanation, missing evidence, conflicting amount/item identity, ambiguity,
customer ownership, typed evidence, and atomic persistence. Preserve the latest-bill and
current-plan regression suites. Do not use a model judge for deterministic account facts.

## Implementation Steps

1. Obtain approval for the exact synthetic roaming event and supported user-facing conclusion.
2. Define failing service and synthetic-adapter contract tests.
3. Add typed charge evidence and deterministic consistency checks.
4. Persist charge evidence and message links atomically through a forward migration.
5. Extend the existing message API behavior without adding a direct charge endpoint.
6. Update runbooks, decisions, architecture flow, learning notes, and blog.
7. Run automated and localhost verification, then request independent human verification.

## Open Questions

None.

## Decisions

- Start with the single approved roaming line item rather than a general-purpose charge classifier.
- Keep wording deterministic until evidence and safety behavior have their own verified baseline.
- Never treat presence of a line item alone as proof of its cause.
- Use the human-approved July 18, 2026 United States mobile-data event, which automatically
  activated the Synthetic KDDI Overseas Data Day Pass for JPY 1,200.

## Discoveries

- The latest-bill snapshot supplies amount and description evidence but intentionally contains no
  causal event; a second typed evidence source is required for a grounded `why` answer.
- The existing three answer statuses can express this focused behavior without a public schema
  change: ambiguous or unavailable causes use `unavailable` with `uncertain: true` and a clear next
  step.

## Progress

- [x] Confirmed the next MVP slice.
- [x] Recorded the agreed architecture boundary.
- [x] Approved the synthetic supporting event.
- [x] Added failing behavioral tests.
- [x] Implemented the focused investigation.
- [x] Updated runbooks and durable documentation.
- [x] Completed automated verification.
- [x] Completed localhost verification after the existing server was restarted.
- [x] Received independent human verification.

## Verification

Unit, contract, API, migration, and PostgreSQL integration tests pass. The full suite passes 85
tests with integration coverage; Ruff and strict mypy pass across 59 source files. Migration
`20260826_04` is at head and `alembic check` reports no drift. The current-plan regression remains
10/10 routine and 6/6 safety. The human restarted the localhost server and reproduced a grounded,
certain explanation containing the approved event, the nonjudgmental next step, one
`bill_snapshot`, and one `charge_snapshot`.

## Result

The first unexpected-charge investigation is complete. It explains only the approved roaming item
when reconciled bill evidence and confirmed causal evidence agree, safely distinguishes missing,
stale, conflicting, and ambiguous inputs, persists both evidence types atomically, and never decides
a dispute. Automated and independent human verification pass; the slice is ready for its
development checkpoint.
